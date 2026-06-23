from dataclasses import dataclass, field


@dataclass
class SiteData:
    no: int = 0
    area: str = ""
    nama_site: str = ""
    site_id: str = ""
    site_type: str = ""
    id_pelanggan_pln: str = ""
    daya_pln_kva: str = ""
    jumlah_phase: str = ""
    koordinat: str = ""
    daya_actual_w: str = ""
    area_space_m2: str = ""

    def to_csv_row(self):
        return [
            str(self.no),
            self.area,
            self.nama_site,
            self.site_id,
            self.site_type,
            self.id_pelanggan_pln,
            self.daya_pln_kva,
            self.jumlah_phase,
            self.koordinat,
            self.daya_actual_w,
            self.area_space_m2,
        ]

    def to_xlsx_row(self):
        def _int(val):
            try:
                return int(val)
            except (ValueError, TypeError):
                return val

        def _float(val):
            try:
                return float(val.replace(",", "."))
            except (ValueError, TypeError, AttributeError):
                return val

        return [
            _int(self.no),
            self.area,
            self.nama_site,
            self.site_id,
            self.site_type,
            self.id_pelanggan_pln,
            self.daya_pln_kva,
            _int(self.jumlah_phase),
            self.koordinat,
            _int(self.daya_actual_w),
            _float(self.area_space_m2),
        ]

    @staticmethod
    def csv_headers():
        return [
            "NO", "Area", "Nama Site", "Site ID", "Site Type",
            "ID Pelanggan PLN", "Daya PLN (kVA)", "Jumlah Phase",
            "Koordinat", "Daya Actual (W)", "Area Space(m2)",
        ]
