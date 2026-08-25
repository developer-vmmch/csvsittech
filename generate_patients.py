import pandas as pd
from datetime import datetime, timedelta
import random

def generate_patient_dataset():
    start_date = datetime(2026, 5, 1)
    end_date = datetime(2026, 8, 25)
    records_per_day = 300
    
    current_date = start_date
    patient_id_counter = 2601010001
    op_number_counter = 26100000
    
    data = []
    
    first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Heidi"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    cities = ["Karaikal", "Nagapattinam", "Thanjavur", "Tiruchirappalli", "Puducherry"]
    
    while current_date <= end_date:
        for i in range(records_per_day):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            gender = random.choice(["Male", "Female"])
            
            # random dob
            age = random.randint(18, 80)
            dob = current_date - timedelta(days=age*365 + random.randint(0, 364))
            
            mobile = f"9{random.randint(100000000, 999999999)}"
            
            data.append({
                'patient_id': str(patient_id_counter),
                'op_number': str(op_number_counter),
                'registration_date': current_date.strftime('%Y-%m-%d'),
                'first_name': fname,
                'last_name': lname,
                'full_name': f"{fname} {lname}",
                'gender': gender,
                'date_of_birth': dob.strftime('%Y-%m-%d'),
                'age': age,
                'mobile_number': mobile,
                'alternate_phone': '',
                'email': f"{fname.lower()}.{lname.lower()}{random.randint(1,100)}@example.com",
                'address_line1': f"{random.randint(1, 100)} Main Street",
                'address_line2': '',
                'city': random.choice(cities),
                'state': 'Puducherry' if random.random() > 0.5 else 'Tamil Nadu',
                'country': 'India',
                'pincode': '609602',
                'blood_group': random.choice(['O+', 'A+', 'B+', 'AB+', 'O-', 'A-']),
                'marital_status': random.choice(['Single', 'Married']),
                'emergency_contact_name': f"{random.choice(first_names)} {lname}",
                'emergency_contact_phone': f"9{random.randint(100000000, 999999999)}"
            })
            
            patient_id_counter += 1
            op_number_counter += 1
            
        current_date += timedelta(days=1)
        
    df = pd.DataFrame(data)
    
    # Save to Excel
    filename = 'VMMC_ERP_Patient_Import_May01_to_Aug25_2026.xlsx'
    print(f"Generating {len(df)} records in {filename}...")
    df.to_excel(filename, index=False)
    print("Done!")

if __name__ == '__main__':
    generate_patient_dataset()
