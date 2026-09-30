import os
import base64
import io
from typing import Dict, Any, Optional
import qrcode
from django.conf import settings
from django.utils import timezone


class StickerRenderer:
    """
    Renders compact thermal stickers for OP and Review patient visits.
    Produces both HTML (for browser preview / browser print) and raw PRN (TSPL)
    for direct hardware thermal printers (TVS LP 46 Neo, LP 44, TSC, Zebra).
    """

    def __init__(self, width: Optional[str] = None, height: Optional[str] = None):
        self.width = width or getattr(settings, 'STICKER_PRINTER_WIDTH', '60mm')
        self.height = height or getattr(settings, 'STICKER_PRINTER_HEIGHT', '30mm')
        self.include_nabh = getattr(settings, 'STICKER_PRINTER_INCLUDE_NABH', False)

    def extract_sticker_data(self, token_obj) -> Dict[str, Any]:
        """
        Extracts verified print data from a PublicPrintToken instance.
        """
        patient = token_obj.patient
        visit = token_obj.visit
        print_type = (token_obj.print_type or 'OP').upper()

        # Determine visit date
        if visit and visit.visit_date:
            v_date = visit.visit_date
        elif patient.created_at:
            v_date = patient.created_at
        else:
            v_date = timezone.now()

        formatted_date = v_date.strftime('%d/%m/%Y')

        # Department
        dept = (visit.department if visit and visit.department else patient.department) or "GENERAL MEDICINE"
        
        # OP Number
        op_num = patient.op_number or patient.patient_id

        # Public QR URL
        qr_url = token_obj.get_public_url()

        return {
            'print_type': print_type,
            'sticker_label': 'REVIEW' if print_type == 'REVIEW' else 'OP',
            'name': patient.name.upper(),
            'title': patient.title or '',
            'uhid': patient.patient_id,
            'op_number': op_num,
            'department': dept.upper(),
            'visit_date': formatted_date,
            'gender': patient.gender,
            'age': f"{patient.age_years} Y",
            'qr_url': qr_url,
            'token': token_obj.token,
        }

    def generate_qr_base64(self, text: str, box_size: int = 3, border: int = 1) -> str:
        """
        Generates a PNG QR code encoded in Base64 data URI.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('ascii')

    def render_html(self, data: Dict[str, Any]) -> str:
        """
        Renders a pixel-perfect, clean thermal sticker HTML snippet
        strictly adhering to the visual reference design.
        """
        qr_base64 = self.generate_qr_base64(data['qr_url'], box_size=3, border=0)
        sticker_type = data.get('sticker_label', 'OP')
        logo_url = "/static/images/vmmc_logo.png"
        nabh_url = "/static/images/nabh_logo.png"

        nabh_html = ""
        if self.include_nabh:
            nabh_html = f"""<img src="{nabh_url}" style="height: 14px; width: auto; object-fit: contain; margin-left: 4px;" alt="NABH">"""

        html = f"""
        <div class="thermal-sticker sticker-{sticker_type.lower()}" style="
            width: {self.width};
            min-height: {self.height};
            max-height: {self.height};
            background: #ffffff;
            color: #000000;
            border: 1px solid #1e293b;
            box-sizing: border-box;
            padding: 4px 6px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            overflow: hidden;
            position: relative;
            margin: 0 auto;
        ">
            <!-- Header Row -->
            <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1.5px solid #000; padding-bottom: 2px; margin-bottom: 3px;">
                <div style="display: flex; align-items: center; gap: 4px;">
                    <img src="{logo_url}" style="width: 15px; height: 15px; object-fit: contain;" alt="VMMC">
                    <span style="font-size: 9.5px; font-weight: 800; letter-spacing: 0.3px;">VMMC KARAIKAL</span>
                    {nabh_html}
                </div>
                <div style="
                    font-size: 9px;
                    font-weight: 900;
                    background: #000000;
                    color: #ffffff;
                    padding: 0 4px;
                    border-radius: 2px;
                    letter-spacing: 0.5px;
                ">{sticker_type}</div>
            </div>

            <!-- Body: Details (Left) + QR Code (Right) -->
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 4px; flex: 1;">
                <div style="flex: 1; font-size: 8px; line-height: 1.25; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    <div style="font-weight: 800; font-size: 8.5px; text-transform: uppercase; margin-bottom: 1px;">
                        <span style="color: #475569;">Name:</span> {data['name']}
                    </div>
                    <div><span style="color: #475569;">UHID:</span> <span style="font-weight: 800;">{data['uhid']}</span></div>
                    <div><span style="color: #475569;">OP No:</span> <span style="font-weight: 800;">{data['op_number']}</span></div>
                    <div style="overflow: hidden; text-overflow: ellipsis;"><span style="color: #475569;">Dept:</span> {data['department']}</div>
                    <div><span style="color: #475569;">Date:</span> {data['visit_date']}</div>
                </div>

                <!-- QR Code Box -->
                <div style="width: 52px; height: 52px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                    <img src="{qr_base64}" style="width: 50px; height: 50px; display: block;" alt="Sticker QR">
                </div>
            </div>
        </div>
        """
        return html

    def render_prn(self, data: Dict[str, Any]) -> str:
        """
        Renders raw TSPL / PRN commands suitable for TVS thermal printers (e.g. TVS LP 46 Neo / LP 44).
        Standard TSPL command syntax.
        """
        # Parse width/height in mm (strip non-numeric)
        w_mm = "".join(c for c in str(self.width) if c.isdigit() or c == '.') or "60"
        h_mm = "".join(c for c in str(self.height) if c.isdigit() or c == '.') or "30"
        sticker_type = data.get('sticker_label', 'OP')

        prn_commands = [
            f"SIZE {w_mm} mm, {h_mm} mm",
            "GAP 2 mm, 0 mm",
            "DIRECTION 1",
            "CLS",
            f'TEXT 16,10,"2",0,1,1,"VMMC KARAIKAL  {sticker_type}"',
            "BAR 16,32,440,2",
            f'TEXT 16,40,"1",0,1,1,"Name : {data["name"][:24]}"',
            f'TEXT 16,65,"1",0,1,1,"UHID : {data["uhid"]}"',
            f'TEXT 16,90,"1",0,1,1,"OP No: {data["op_number"]}"',
            f'TEXT 16,115,"1",0,1,1,"Dept : {data["department"][:20]}"',
            f'TEXT 16,140,"1",0,1,1,"Date : {data["visit_date"]}"',
            f'QRCODE 310,40,M,4,A,0,"{data["qr_url"]}"',
            "PRINT 1",
            ""
        ]
        return "\r\n".join(prn_commands)
