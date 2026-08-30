import hashlib
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from lxml import etree

from facturacion.models import (
    Company,
    DGIICertificationDocument,
    DGIICertificationEvent,
    DGIICertificationItem,
    DGIICertificationPlan,
)
from facturacion.services.certification_locking import (
    CertificationArtifactChanged,
    CertificationMutationBlocked,
)
from facturacion.services.dgii_certification import (
    CertificationArtifactFence,
    CertificationDocumentFence,
    CertificationPreparedArtifactPublisher,
    CertificationPreparedSignature,
    DGIICertificationDocumentGenerator,
    DGIICertificationDocumentSigner,
    PreparedCertificationDocument,
    PreparedCertificationSignature,
)


class CertificationPreparedPublishingTests(TransactionTestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.override.enable()
        self.company = Company.objects.create(name='Prepared Publisher', rnc='101998001')
        self.plan = DGIICertificationPlan.objects.create(
            company=self.company, source_filename='prepared.xlsx', file_sha256='8' * 64,
        )

    def tearDown(self):
        self.override.disable()
        self.media_dir.cleanup()

    def _item(self, encf='E310000000001', *, ecf_type='31', group=1, row=1, raw=None):
        return DGIICertificationItem.objects.create(
            plan=self.plan, company=self.company, ecf_type=ecf_type, dgii_group=group,
            encf=encf, source_sheet='ECF', source_row=row, raw_data=raw or {},
        )

    def _document(self, item, *, status='generated', xml='<old/>'):
        return DGIICertificationDocument.objects.create(
            plan=self.plan, company=self.company, item=item, ecf_type=item.ecf_type,
            encf=item.encf, status=status, xml_content=xml,
            xml_hash=hashlib.sha256(xml.encode()).hexdigest() if xml else '',
            generated_at=timezone.now() if xml else None,
        )

    def _generator(self):
        class Builder:
            @staticmethod
            def build(payload):
                return etree.Element('PreparedECF')

        class Factory:
            @staticmethod
            def get(ecf_type):
                return Builder()

        generator = DGIICertificationDocumentGenerator(builder_factory=Factory())
        generator._resolve_issuer = lambda company: object()
        generator._build_payload = lambda **kwargs: object()
        return generator

    def _prepared_document(self, item, document=None, *, dependencies=()):
        generator = self._generator()
        fence = generator.document_fence(item=item, document=document)
        return generator.prepare_item(
            item_snapshot=item, target_fence=fence, dependency_fences=dependencies,
            integral_signature_value='ABC123-source-signature' if item.ecf_type == 'RFCE' else None,
        )

    def _prepared_signature(self, prepared_document, *, content=b'<signed-prepared/>'):
        digest = hashlib.sha256(content).hexdigest()
        path = default_storage.save(
            f'prepared/{threading.get_ident()}-{digest}.xml', ContentFile(content),
        )
        return PreparedCertificationSignature(prepared_document, path, digest, 'test', ())

    def test_suite_runs_against_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')

    def test_prepare_item_does_not_persist_document_item_or_events(self):
        item = self._item()
        before = (item.status, item.updated_at)
        prepared = self._prepared_document(item)
        item.refresh_from_db()
        self.assertTrue(prepared.xml_content)
        self.assertEqual((item.status, item.updated_at), before)
        self.assertFalse(DGIICertificationDocument.objects.filter(item=item).exists())
        self.assertFalse(DGIICertificationEvent.objects.filter(item=item).exists())

    def test_rfce_uses_exact_explicit_integral_signature_without_database_lookup(self):
        item = self._item(
            'E320000000011', ecf_type='RFCE', group=3,
            raw={'RNCEmisor': '101998001', 'MontoTotal': '100.00'},
        )
        generator = self._generator()
        with patch.object(generator, '_integral_invoice_signature_value', side_effect=AssertionError('DB lookup')):
            prepared = generator.prepare_item(
                item_snapshot=item,
                target_fence=generator.document_fence(item=item),
                integral_signature_value='ABC123-signature-value',
            )
        self.assertIn('<CodigoSeguridadeCF>ABC123</CodigoSeguridadeCF>', prepared.xml_content)

    def test_prepare_document_creates_unreferenced_blob_without_database_changes(self):
        item = self._item()
        document = self._document(item)
        prepared_document = self._prepared_document(item, document)
        signer = DGIICertificationDocumentSigner()
        content = b'<signed-from-prepared/>'
        digest = hashlib.sha256(content).hexdigest()
        path = default_storage.save('prepared/signer.xml', ContentFile(content))
        signer._prepare_signature = lambda snapshot: CertificationPreparedSignature(
            snapshot, path, digest, 'test', (),
        )
        before = (document.status, document.signed_xml_path, document.signed_xml_hash, document.signed_at)
        prepared_signature = signer.prepare_document(prepared_document=prepared_document)
        document.refresh_from_db()
        self.assertEqual((document.status, document.signed_xml_path, document.signed_xml_hash, document.signed_at), before)
        self.assertTrue(default_storage.exists(prepared_signature.storage_path))
        self.assertFalse(DGIICertificationEvent.objects.filter(item=item).exists())

    def test_prepare_document_signing_failure_does_not_publish_state(self):
        item = self._item()
        document = self._document(item)
        prepared_document = self._prepared_document(item, document)
        signer = DGIICertificationDocumentSigner()
        with patch.object(signer, '_prepare_signature', side_effect=ValueError('signing failure')):
            with self.assertRaisesRegex(ValueError, 'signing failure'):
                signer.prepare_document(prepared_document=prepared_document)
        document.refresh_from_db()
        self.assertEqual(document.status, DGIICertificationDocument.STATUS_GENERATED)
        self.assertFalse(document.signed_xml_path)
        self.assertFalse(DGIICertificationEvent.objects.filter(item=item).exists())

    def test_prepare_document_storage_failure_does_not_publish_state(self):
        item = self._item()
        document = self._document(item)
        prepared_document = self._prepared_document(item, document)
        signer = DGIICertificationDocumentSigner()
        with patch.object(signer, '_prepare_signature', side_effect=OSError('storage failure')):
            with self.assertRaisesRegex(OSError, 'storage failure'):
                signer.prepare_document(prepared_document=prepared_document)
        document.refresh_from_db()
        self.assertEqual(document.status, DGIICertificationDocument.STATUS_GENERATED)
        self.assertFalse(document.signed_xml_path)
        self.assertFalse(DGIICertificationEvent.objects.filter(item=item).exists())

    def test_joint_publication_creates_absent_target_atomically(self):
        item = self._item()
        prepared_document = self._prepared_document(item)
        prepared_signature = self._prepared_signature(prepared_document)
        result = CertificationPreparedArtifactPublisher().publish_document_and_signature(
            prepared_document=prepared_document, prepared_signature=prepared_signature,
        )
        self.assertEqual(result.status, 'signed')
        self.assertEqual(result.xml_hash, prepared_document.xml_hash)
        self.assertEqual(result.signed_xml_hash, prepared_signature.signed_xml_hash)
        self.assertEqual(DGIICertificationEvent.objects.filter(item=item).count(), 2)

    def test_dependency_stale_blocks_and_cleans_prepared_blob(self):
        source_item = self._item('E320000000011', group=4, row=1)
        source = self._document(source_item, status='signed')
        source.signed_xml_path = default_storage.save('source/signed.xml', ContentFile(b'<source/>'))
        source.signed_xml_hash = hashlib.sha256(b'<source/>').hexdigest()
        source.signed_at = timezone.now()
        source.save(update_fields=['signed_xml_path', 'signed_xml_hash', 'signed_at', 'updated_at'])
        dependency = CertificationArtifactFence(
            source.plan_id, source.company_id, source.item_id, source.pk, source.xml_hash,
            source.signed_xml_path, source.signed_xml_hash, source.signed_at,
        )
        target_item = self._item('E320000000011', ecf_type='RFCE', group=3, row=2)
        prepared_document = self._prepared_document(target_item, dependencies=(dependency,))
        prepared_signature = self._prepared_signature(prepared_document)
        DGIICertificationDocument.objects.filter(pk=source.pk).update(signed_xml_hash='a' * 64)
        with self.assertRaises(CertificationArtifactChanged):
            CertificationPreparedArtifactPublisher().publish_document_and_signature(
                prepared_document=prepared_document, prepared_signature=prepared_signature,
            )
        self.assertFalse(DGIICertificationDocument.objects.filter(item=target_item).exists())
        self.assertFalse(default_storage.exists(prepared_signature.storage_path))

    def test_existing_target_stale_blocks_publication(self):
        item = self._item()
        document = self._document(item)
        prepared_document = self._prepared_document(item, document)
        prepared_signature = self._prepared_signature(prepared_document)
        DGIICertificationDocument.objects.filter(pk=document.pk).update(xml_hash='b' * 64)
        with self.assertRaises(CertificationArtifactChanged):
            CertificationPreparedArtifactPublisher().publish_document_and_signature(
                prepared_document=prepared_document, prepared_signature=prepared_signature,
            )

    def test_absent_target_created_concurrently_blocks_publication(self):
        item = self._item()
        prepared_document = self._prepared_document(item)
        prepared_signature = self._prepared_signature(prepared_document)
        self._document(item)
        with self.assertRaises(CertificationArtifactChanged):
            CertificationPreparedArtifactPublisher().publish_document_and_signature(
                prepared_document=prepared_document, prepared_signature=prepared_signature,
            )

    def test_outcome_changed_to_blocking_rejects_publication(self):
        item = self._item()
        document = self._document(item)
        prepared_document = self._prepared_document(item, document)
        prepared_signature = self._prepared_signature(prepared_document)
        document.submission_outcome = 'unknown'
        document.save(update_fields=['submission_outcome', 'updated_at'])
        with self.assertRaises(CertificationMutationBlocked):
            CertificationPreparedArtifactPublisher().publish_document_and_signature(
                prepared_document=prepared_document, prepared_signature=prepared_signature,
            )

    def test_two_concurrent_absent_target_publications_only_one_wins(self):
        item = self._item()
        prepared_document = self._prepared_document(item)
        signatures = [
            self._prepared_signature(prepared_document, content=f'<signed-{index}/>'.encode())
            for index in range(2)
        ]
        barrier = threading.Barrier(2)

        def worker(signature):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                CertificationPreparedArtifactPublisher().publish_document_and_signature(
                    prepared_document=prepared_document, prepared_signature=signature,
                )
                return 'published'
            except CertificationArtifactChanged:
                return 'stale'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=20) for future in (
                pool.submit(worker, signatures[0]), pool.submit(worker, signatures[1]),
            )]
        self.assertEqual(results.count('published'), 1)
        self.assertEqual(results.count('stale'), 1)
        self.assertEqual(DGIICertificationDocument.objects.filter(item=item).count(), 1)

    def test_storage_hash_mismatch_leaves_database_untouched(self):
        item = self._item()
        prepared_document = self._prepared_document(item)
        signature = self._prepared_signature(prepared_document)
        bad_signature = PreparedCertificationSignature(
            prepared_document, signature.storage_path, 'f' * 64, 'test', (),
        )
        with self.assertRaises(CertificationArtifactChanged):
            CertificationPreparedArtifactPublisher().publish_document_and_signature(
                prepared_document=prepared_document, prepared_signature=bad_signature,
            )
        self.assertFalse(DGIICertificationDocument.objects.filter(item=item).exists())

    def test_event_failure_rolls_back_joint_publication_and_cleans_blob(self):
        item = self._item()
        prepared_document = self._prepared_document(item)
        signature = self._prepared_signature(prepared_document)
        with patch.object(DGIICertificationEvent.objects, 'create', side_effect=RuntimeError('event failure')):
            with self.assertRaises(RuntimeError):
                CertificationPreparedArtifactPublisher().publish_document_and_signature(
                    prepared_document=prepared_document, prepared_signature=signature,
                )
        self.assertFalse(DGIICertificationDocument.objects.filter(item=item).exists())
        self.assertFalse(default_storage.exists(signature.storage_path))

    def test_cleanup_does_not_delete_currently_referenced_path(self):
        item = self._item()
        document = self._document(item, status='signed')
        path = default_storage.save('current/signed.xml', ContentFile(b'<current/>'))
        document.signed_xml_path = path
        document.save(update_fields=['signed_xml_path', 'updated_at'])
        CertificationPreparedArtifactPublisher.cleanup_unreferenced(path)
        self.assertTrue(default_storage.exists(path))
