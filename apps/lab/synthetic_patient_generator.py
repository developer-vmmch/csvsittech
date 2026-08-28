import random

class SyntheticPatientGenerator:
    FIRST_NAMES_MALE = ["Arun", "Ramesh", "Suresh", "Vijay", "Karthik", "Ravi", "Vikas", "Sanjay", "Amit", "Rahul", "Prakash", "Ganesh", "Ashok", "Rajesh", "Naveen"]
    FIRST_NAMES_FEMALE = ["Priya", "Anjali", "Kavita", "Sneha", "Lakshmi", "Meena", "Geeta", "Sunita", "Anita", "Divya", "Pooja", "Rekha", "Renu", "Swati", "Aarti"]
    LAST_NAMES = ["Kumar", "Singh", "Sharma", "Verma", "Yadav", "Gupta", "Das", "Patel", "Reddy", "Rao", "Nair", "Iyer", "Chauhan", "Jain", "Mishra"]
    
    GUARDIAN_NAMES_MALE = ["Ramesh Kumar", "Suresh Kumar", "Rajendra Singh", "Ashok Sharma", "Ram Prasad", "Mohan Das", "Dinesh Verma", "Prakash Yadav", "Sanjay Gupta", "Ganesh Patel"]
    
    STREETS = ["Main Street", "Lake Road", "Gandhi Street", "Park Avenue", "Hospital Road", "North Street", "South Avenue", "East Road", "West Lane", "Station Road"]
    AREAS = ["Central Area", "Civil Lines", "New Extension", "Old City", "Market Area", "Colony"]
    CITIES = ["Karaikal", "Puducherry", "Chennai", "Coimbatore", "Madurai", "Trichy", "Salem"]
    
    @classmethod
    def generate(cls, source_patient):
        """Generates synthetic demographics based on the source patient's gender/title."""
        gender = source_patient.gender or 'Male'
        title = source_patient.title or 'Mr'
        
        # Name generation
        if gender.lower() == 'female' or title in ['Mrs', 'Ms']:
            first_name = random.choice(cls.FIRST_NAMES_FEMALE)
        else:
            first_name = random.choice(cls.FIRST_NAMES_MALE)
            
        last_name = random.choice(cls.LAST_NAMES)
        name = f"{first_name} {last_name}"
        
        # Guardian generation
        guardian_name = random.choice(cls.GUARDIAN_NAMES_MALE)
        guardian_title = 'Mr'
        
        # Address generation
        house_num = random.randint(1, 999)
        street = random.choice(cls.STREETS)
        area = random.choice(cls.AREAS)
        city = random.choice(cls.CITIES)
        pincode = str(random.randint(600000, 699999))
        
        address = f"{house_num} {street}"
        
        # Phone generation
        phone = f"9{random.randint(100000000, 999999999)}"
        
        return {
            'name': name,
            'title': title,
            'guardian_name': guardian_name,
            'guardian_title': guardian_title,
            'street': address,
            'village_area': area,
            'city': city,
            'state': source_patient.state or 'Puducherry',
            'pincode': pincode,
            'mobile_no': phone,
            'guardian_phone': phone,
        }
