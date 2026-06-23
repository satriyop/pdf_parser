import pytest

from pdf_parser.models import SiteData


@pytest.fixture
def sample_sites():
    return [
        SiteData(
            no=1,
            area="EAST JAVA",
            nama_site="SITE_ALPHA",
            site_id="SITE001",
            site_type="Outdoor",
            id_pelanggan_pln="PLN001",
            daya_pln_kva="10",
            jumlah_phase="3",
            koordinat="lat= -7.8\nlng= 114.1",
            daya_actual_w="1500",
            area_space_m2="3.2",
        ),
        SiteData(
            no=2,
            area="EAST JAVA",
            nama_site="SITE_BETA",
            site_id="SITE002",
            site_type="Indoor",
            jumlah_phase="1",
            daya_actual_w="800",
            area_space_m2="6.0",
        ),
    ]


@pytest.fixture
def sample_pdf_path():
    import glob
    pdfs = sorted(glob.glob("*.pdf"))
    return pdfs[0] if pdfs else None
