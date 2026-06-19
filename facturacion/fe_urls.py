from django.urls import path

from facturacion.api.views.dgii_public import (
    FECommercialApprovalView,
    FECertificateValidationView,
    FEReceptionView,
    FESeedView,
)


urlpatterns = [
    path('recepcion/api/ecf', FEReceptionView.as_view(), name='fe-recepcion-ecf'),
    path('aprobacioncomercial/api/ecf', FECommercialApprovalView.as_view(), name='fe-aprobacion-comercial-ecf'),
    path('autenticacion/api/semilla', FESeedView.as_view(), name='fe-autenticacion-semilla'),
    path(
        'autenticacion/api/semillavalidacioncertificado',
        FECertificateValidationView.as_view(),
        name='fe-autenticacion-semilla-validacion-certificado',
    ),
]
