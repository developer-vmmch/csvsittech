"""
Management command: generate_dummy_patients
Creates synthetic dummy patients for testing (patient_type=D).
"""
import random
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.patients.models import Patient, Department


FIRST_NAMES_MALE = [
    "ARUN","SURESH","RAVI","KARTHIK","MURUGAN","KUMAR","SELVAM","ANAND",
    "SENTHIL","RAMESH","VIMAL","BALA","VIJAY","MANOJ","DEEPAK","RAJESH",
    "GOPAL","KANNAN","SIVA","PRAKASH","DURAI","SARATH","MANI","PANDIAN",
    "DINESH","VELMURUGAN","ARJUN","SANTHOSH","PRABHU","HARI",
    "ANBARASAN","BOOPATHI","CHELLADURAI","ELAVARASAN",
    "GANESAN","HARISH","ILAYARAJA","JAYAKUMAR","LOGESH","NANDAKUMAR"
]
FIRST_NAMES_FEMALE = [
    "PRIYA","MEENA","KAVYA","LAKSHMI","SELVI","DIVYA","UMA","GEETHA",
    "ANUSHA","REVATHI","SHANTHI","MALATHI","VALLI","KAMALA","NALINI",
    "RADHA","SUDHA","PADMA","SARANYA","DEEPA","NITHYA","VIJAYALAKSHMI",
    "BRINDHA","ANITHA","SEETHA","SANGEETHA","AMUDHA","RENUKA","MALAR","THILAGA",
    "KALPANA","HEMALATHA","PARVATHY","GAYATHRI","BHARATHI","INDIRA",
    "JAYANTHI","KALAVATHI","LAVANYA","MYTHILI"
]
LAST_NAMES = [
    "KUMAR","MURUGAN","SELVAM","RAJAN","PANDIAN","KRISHNAN","PILLAI",
    "NAIR","DAS","NAIDU","SUBRAMANIAN","CHANDRASEKARAN","AYYAPPAN",
    "MUTHUSAMY","NATARAJAN","RAMASAMY","PERIASAMY","SUBRAMANIAM","ARUMUGAM",
    "VENKATESAN","THANGARAJ","MUTHU","ANNAMALAI","CHINNASWAMY","GOVINDARAJ"
]
STREET_NAMES = [
    "12, Gandhi Street","45, Nehru Road","8, Anna Salai","23, Market Street",
    "67, Beach Road","3, Temple Lane","89, Cross Cut Road","14, New Colony",
    "56, East Coast Road","31, VGP Nagar","77, Vaigai Street","5, Kaveri Nagar",
    "18, Pondy Road","42, Selvam Nagar","9, Railway Colony","25, Hospital Road",
    "60, NS Road","37, South Street","11, Fishermen Colony","50, Kaliamman Koil Street",
]
AREAS = [
    "Karaikal","Nagapattinam","Mayiladuthurai","Kumbakonam","Sirkazhi",
    "Tirukadaiyur","Tharangambadi","Porayar","Sembanarkoil","Kollidam"
]
BLOOD_GROUPS = ["A+","A-","B+","B-","AB+","AB-","O+","O-"]
AGE_GROUPS = [(1,12,"pediatric"),(13,17,"teen"),(18,45,"adult"),(46,65,"middle"),(66,85,"elderly")]


def get_age_gender():
    weights = [10,8,50,22,10]
    grp = random.choices(AGE_GROUPS, weights=weights)[0]
    age = random.randint(grp[0], grp[1])
    gender = random.choice(["Male","Female","Male","Female","Male"])
    if grp[2] == "pediatric":
        gender = random.choice(["Male","Female"])
        title = "Master" if gender == "Male" else "Baby"
    elif gender == "Male":
        title = "Mr"
    else:
        title = "Mrs" if age >= 18 else "Miss"
    return age, gender, title, grp[2]


def get_guardian(age, gender, grp):
    gphone = f"9{random.randint(100000000,999999999)}"
    if grp in ("pediatric","teen"):
        return "Mr","FATHER","F/O",gphone
    elif gender == "Female":
        return "Mr","HUSBAND","H/O",gphone
    else:
        return "Mrs","WIFE","W/O",gphone


class Command(BaseCommand):
    help = "Generate 200 dummy patients (patient_type=D) for testing"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=200)
        parser.add_argument("--start-id", type=str, default="2699000001")

    def handle(self, *args, **options):
        count = options["count"]
        patient_id = int(options["start_id"])
        existing_ids = set(Patient.objects.values_list("patient_id", flat=True))
        existing_ops = set(Patient.objects.values_list("op_number", flat=True))
        depts = list(Department.objects.filter(is_active=True))
        if not depts:
            self.stdout.write(self.style.ERROR("No active departments"))
            return
        today = datetime.date.today()
        created = 0
        skipped = 0
        batch = []
        self.stdout.write(f"Generating {count} dummy patients...")
        while created + len(batch) < count:
            pid = str(patient_id)
            opn = f"D{patient_id}"
            if pid in existing_ids or opn in existing_ops:
                patient_id += 1
                skipped += 1
                if skipped > 50000:
                    break
                continue
            existing_ids.add(pid)
            existing_ops.add(opn)
            days_back = random.randint(0, 29)
            reg_date = today - datetime.timedelta(days=days_back)
            age, gender, title, grp = get_age_gender()
            dob = reg_date - datetime.timedelta(days=age*365+random.randint(0,364))
            fname = random.choice(FIRST_NAMES_MALE if gender == "Male" else FIRST_NAMES_FEMALE)
            lname = random.choice(LAST_NAMES)
            full_name = f"{fname} {lname}"
            mobile = f"9{random.randint(100000000,999999999)}"
            g_title, g_name, g_rel, g_phone = get_guardian(age, gender, grp)
            weighted_depts = depts + depts + [d for d in depts if d.code in ("GM","PED","EMR","GYN","OBS")]
            dept = random.choice(weighted_depts)
            visit_through = random.choices(["OP","IP"], weights=[70,30])[0]
            p = Patient(
                patient_id=pid,
                op_number=opn,
                title=title,
                name=full_name,
                gender=gender,
                dob=dob,
                age_years=age,
                age_months=0,
                age_days=0,
                mobile_no=mobile,
                street=random.choice(STREET_NAMES),
                city=random.choice(AREAS),
                village_area="",
                state="Puducherry",
                country="India",
                pincode="609602",
                blood_group=random.choice(BLOOD_GROUPS),
                guardian_title=g_title,
                guardian_name=g_name,
                guardian_relationship=g_rel,
                guardian_phone=g_phone,
                department=dept.name,
                department_obj=dept,
                visit_through=visit_through,
                registration_date=reg_date,
                patient_type="D",
                created_source="D",
                centre="VMMCH",
                category="CONSULTATION",
            )
            batch.append(p)
            patient_id += 1
            if len(batch) >= 50:
                with transaction.atomic():
                    Patient.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)
                self.stdout.write(f"  Created {created}/{count}...")
                batch = []
        if batch:
            with transaction.atomic():
                Patient.objects.bulk_create(batch, ignore_conflicts=True)
            created += len(batch)
        self.stdout.write(self.style.SUCCESS(f"Done! Created {created} dummy patients. Skipped {skipped} ID collisions."))
