"""Stress the fiscal e-CF core with concurrent invoices and reversals."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.db.models import Count, Min, Max
from django.test import override_settings

from facturacion.ecf.services.document_factory import ECFDocumentFactoryService
from facturacion.models import (
    Category,
    Client,
    Company,
    CreditNote,
    ECFIssuerConfig,
    ECFSequence,
    ElectronicFiscalDocument,
    Invoice,
    Product,
)
from facturacion.services.credit_notes import CreditNoteService
from facturacion.services.invoicing import InvoiceCreationService


class Command(BaseCommand):
    help = "Run fiscal stress checks for e-NCF allocation, invoice creation, idempotency and E34 reversals."

    def add_arguments(self, parser):
        parser.add_argument("--invoices", type=int, default=50, help="Number of concurrent invoices to create.")
        parser.add_argument("--workers", type=int, default=8, help="Thread workers used for concurrent operations.")
        parser.add_argument("--items", type=int, default=3, help="Items per generated invoice.")
        parser.add_argument("--reversals", type=int, default=10, help="Concurrent one-unit E34 reversals against one invoice.")
        parser.add_argument("--issuer-rnc", default="101010555", help="Issuer RNC used or created for the stress run.")
        parser.add_argument("--enqueue", action="store_true", help="Allow automatic Celery enqueue. Default keeps stress DB-local.")

    def handle(self, *args, **options):
        if options["workers"] <= 0 or options["invoices"] <= 0:
            raise CommandError("--workers and --invoices must be greater than zero.")

        start = time.perf_counter()
        context = override_settings(ECF_AUTO_ENQUEUE_ENABLED=bool(options["enqueue"]))
        with context:
            company = self._company()
            issuer = self._issuer(options["issuer_rnc"], company)
            self._sequence(issuer, "32", options["invoices"] + 100)
            self._sequence(issuer, "34", options["reversals"] + 100)
            products = self._products(company, options["items"], stock=options["invoices"] * options["items"] + 100)
            client = Client.objects.create(
                company=company,
                name=f"Stress Cliente {int(start)}",
                ruc_ci="",
                email="stress@example.test",
            )

            invoice_results = self._run_invoice_stress(
                issuer=issuer,
                client=client,
                products=products,
                invoices=options["invoices"],
                workers=options["workers"],
            )
            idempotency_result = (
                self._run_idempotency_probe(invoice_results["invoice_ids"][0], issuer, options["workers"])
                if invoice_results["invoice_ids"]
                else {"returned_document_ids": [], "duplicate_documents": True, "error": "No invoices were created."}
            )
            reversal_result = self._run_reversal_stress(
                issuer=issuer,
                workers=options["workers"],
                attempts=options["reversals"],
            )

        elapsed = time.perf_counter() - start
        report = {
            "elapsed_seconds": round(elapsed, 3),
            "settings": {
                "invoices": options["invoices"],
                "workers": options["workers"],
                "items_per_invoice": options["items"],
                "reversals": options["reversals"],
                "celery_enqueue_enabled": bool(options["enqueue"]),
            },
            "invoice_stress": invoice_results,
            "idempotency_probe": idempotency_result,
            "reversal_stress": reversal_result,
            "sequence_integrity": self._sequence_integrity(issuer),
            "document_integrity": self._document_integrity(),
        }
        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))

        reversal_overflow = reversal_result["successful"] > reversal_result["available_quantity"]
        if (
            invoice_results["errors"]
            or invoice_results["duplicate_encfs"]
            or idempotency_result["duplicate_documents"]
            or reversal_overflow
        ):
            raise CommandError("Fiscal stress detected integrity errors. Review JSON report.")

    def _company(self):
        company = Company.objects.filter(is_active=True).order_by("id").first()
        if company:
            return company
        return Company.objects.create(name="Empresa Stress Fiscal", rnc="101010555")

    def _issuer(self, rnc, company):
        issuer, _created = ECFIssuerConfig.objects.get_or_create(
            rnc=rnc,
            defaults={
                "company": company,
                "business_name": "Empresa Stress Fiscal SRL",
                "address": "Calle Stress Fiscal 1",
                "environment": "testing",
                "is_active": True,
            },
        )
        if issuer.company_id != company.id:
            issuer.company = company
            issuer.save(update_fields=["company", "updated_at"])
        return issuer

    def _sequence(self, issuer, ecf_type, minimum_available):
        sequence = (
            ECFSequence.objects
            .filter(issuer=issuer, ecf_type=ecf_type, is_active=True)
            .order_by("next_number")
            .first()
        )
        if sequence and sequence.remaining >= minimum_available:
            return sequence

        start_number = 1
        last = (
            ECFSequence.objects
            .filter(issuer=issuer, ecf_type=ecf_type)
            .order_by("-end_number")
            .first()
        )
        if last:
            start_number = last.end_number + 1

        return ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type=ecf_type,
            start_number=start_number,
            end_number=start_number + minimum_available + 100,
            next_number=start_number,
            is_active=True,
        )

    def _products(self, company, count, stock):
        category, _created = Category.objects.get_or_create(company=company, name="Fiscal Stress")
        products = []
        for index in range(count):
            product, _created = Product.objects.get_or_create(
                company=company,
                barcode=f"STRESS-{index + 1:04d}",
                defaults={
                    "name": f"Producto Stress {index + 1}",
                    "description": "Producto para stress fiscal",
                    "price": Decimal("100.00") + index,
                    "stock": stock,
                    "category": category,
                },
            )
            if product.stock < stock:
                product.stock = stock
                product.save(update_fields=["stock"])
            products.append(product)
        return products

    def _run_invoice_stress(self, issuer, client, products, invoices, workers):
        errors = []
        invoice_ids = []
        encfs = []

        def create_one(index):
            close_old_connections()
            try:
                details = [
                    {"product": product.id, "quantity": 1, "price": product.price}
                    for product in products
                ]
                result = InvoiceCreationService().create_invoice(
                    client_id=client.id,
                    details=details,
                    payment_method="cash",
                    receipt_type="invoice",
                    status="paid",
                    discount=Decimal("0.00"),
                    issuer_id=issuer.id,
                    ecf_type="32",
                    company=issuer.company,
                )
                return {"invoice_id": result.invoice.id, "encf": result.electronic_document.encf, "error": None}
            except Exception as exc:
                return {"invoice_id": None, "encf": None, "error": f"{type(exc).__name__}: {exc}", "index": index}
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(create_one, index) for index in range(invoices)]
            for future in as_completed(futures):
                result = future.result()
                if result["error"]:
                    errors.append(result)
                else:
                    invoice_ids.append(result["invoice_id"])
                    encfs.append(result["encf"])

        return {
            "created": len(invoice_ids),
            "errors": errors,
            "invoice_ids": invoice_ids,
            "duplicate_encfs": sorted([encf for encf in set(encfs) if encfs.count(encf) > 1]),
            "min_encf": min(encfs) if encfs else None,
            "max_encf": max(encfs) if encfs else None,
        }

    def _run_idempotency_probe(self, invoice_id, issuer, workers):
        invoice = Invoice.objects.get(pk=invoice_id)

        def create_document():
            close_old_connections()
            try:
                result = ECFDocumentFactoryService().create_for_invoice(invoice, issuer_id=issuer.id, ecf_type="32")
                return result.document.id
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            document_ids = [future.result() for future in as_completed(pool.submit(create_document) for _ in range(workers))]

        return {
            "returned_document_ids": sorted(set(document_ids)),
            "duplicate_documents": ElectronicFiscalDocument.objects.filter(invoice_id=invoice_id).count() != 1,
        }

    def _run_reversal_stress(self, issuer, workers, attempts):
        user = self._operator()
        product = self._products(issuer.company, 1, stock=attempts + 10)[0]
        result = InvoiceCreationService().create_invoice(
            client_id=None,
            details=[{"product": product.id, "quantity": max(attempts // 2, 1), "price": product.price}],
            payment_method="cash",
            receipt_type="invoice",
            status="paid",
            discount=Decimal("0.00"),
            issuer_id=issuer.id,
            ecf_type="32",
            company=issuer.company,
        )
        origin_document = result.electronic_document
        origin_document.status = "accepted"
        origin_document.track_id = f"stress-track-{origin_document.id}"
        origin_document.xml_content = "<ECF />"
        origin_document.signed_xml_content = "<ECF />"
        origin_document.save(update_fields=["status", "track_id", "xml_content", "signed_xml_content", "updated_at"])
        detail = result.invoice.details.first()

        def reverse_one(index):
            close_old_connections()
            try:
                CreditNoteService().create_credit_note(
                    origin_invoice_id=result.invoice.id,
                    details=[{"origin_detail": detail.id, "quantity": 1}],
                    reason=f"Stress reversal {index}",
                    user=user,
                    issuer_id=issuer.id,
                )
                return {"ok": True, "error": None}
            except Exception as exc:
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            finally:
                close_old_connections()

        outcomes = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(reverse_one, index) for index in range(attempts)]
            outcomes = [future.result() for future in as_completed(futures)]

        return {
            "origin_invoice_id": result.invoice.id,
            "attempts": attempts,
            "available_quantity": detail.quantity,
            "successful": sum(1 for outcome in outcomes if outcome["ok"]),
            "failed": sum(1 for outcome in outcomes if not outcome["ok"]),
            "errors": [outcome["error"] for outcome in outcomes if outcome["error"]],
            "credit_notes_created": CreditNote.objects.filter(origin_invoice=result.invoice).count(),
        }

    def _operator(self):
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username="fiscal-stress-operator",
            defaults={"email": "fiscal-stress@example.test", "is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        elif not user.is_superuser:
            user.is_superuser = True
            user.is_staff = True
            user.save(update_fields=["is_superuser", "is_staff"])
        return user

    def _sequence_integrity(self, issuer):
        data = {}
        for ecf_type in ("32", "34"):
            docs = ElectronicFiscalDocument.objects.filter(issuer=issuer, ecf_type=ecf_type)
            duplicate_rows = (
                docs.values("encf")
                .annotate(total=Count("id"))
                .filter(total__gt=1)
                .values_list("encf", flat=True)
            )
            sequence_state = ECFSequence.objects.filter(issuer=issuer, ecf_type=ecf_type).aggregate(
                min_next=Min("next_number"),
                max_next=Max("next_number"),
            )
            data[ecf_type] = {
                "documents": docs.count(),
                "duplicates": list(duplicate_rows),
                "sequence_state": sequence_state,
            }
        return data

    def _document_integrity(self):
        return {
            "invoice_duplicate_documents": list(
                ElectronicFiscalDocument.objects
                .exclude(invoice_id=None)
                .values("invoice_id")
                .annotate(total=Count("id"))
                .filter(total__gt=1)
            ),
            "credit_note_duplicate_documents": list(
                ElectronicFiscalDocument.objects
                .exclude(credit_note_id=None)
                .values("credit_note_id")
                .annotate(total=Count("id"))
                .filter(total__gt=1)
            ),
        }
