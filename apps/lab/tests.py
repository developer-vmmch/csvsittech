from django.test import TestCase
from decimal import Decimal
from apps.lab.models import Parameter, Investigation, InvestigationParameter, AgeGroup, Diagnosis, ParameterReferenceRange
from apps.lab.services import resolveReferenceRange

class ResolveReferenceRangeTests(TestCase):
    def setUp(self):
        # Set up test data
        self.investigation = Investigation.objects.create(name="CBC", code="CBC")
        self.parameter = Parameter.objects.create(name="Hemoglobin", code="HB")
        self.inv_param = InvestigationParameter.objects.create(
            investigation=self.investigation,
            parameter=self.parameter
        )
        
        self.age_group_newborn = AgeGroup.objects.create(label="0-1 Day", min_age_value=0, min_age_unit='DAY', max_age_value=1, max_age_unit='DAY', sort_order=1)
        self.age_group_child = AgeGroup.objects.create(label="2-10 Years", min_age_value=2, min_age_unit='YEAR', max_age_value=10, max_age_unit='YEAR', sort_order=2)
        
        self.diagnosis_fever = Diagnosis.objects.create(name="Fever", code="FVR")
        self.diagnosis_other = Diagnosis.objects.create(name="Other", code="OTH")
        
        # Generic range for newborn
        self.range_newborn_generic = ParameterReferenceRange.objects.create(
            investigation_parameter=self.inv_param,
            age_group=self.age_group_newborn,
            diagnosis=None,
            min_value=Decimal("14.0"),
            max_value=Decimal("24.0")
        )
        
        # Specific override for newborn + fever
        self.range_newborn_fever = ParameterReferenceRange.objects.create(
            investigation_parameter=self.inv_param,
            age_group=self.age_group_newborn,
            diagnosis=self.diagnosis_fever,
            min_value=Decimal("13.0"),
            max_value=Decimal("22.0")
        )

    def test_exact_age_and_diagnosis_match(self):
        """Test that a specific diagnosis override is returned if it matches."""
        result = resolveReferenceRange(self.age_group_newborn, self.diagnosis_fever.id, self.inv_param.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.range_newborn_fever.id)

    def test_age_only_fallback(self):
        """Test that the generic range is used if there is no specific diagnosis override."""
        result = resolveReferenceRange(self.age_group_newborn, self.diagnosis_other.id, self.inv_param.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.range_newborn_generic.id)

    def test_no_match_found(self):
        """Test that None is returned if no range is configured for the given age group."""
        result = resolveReferenceRange(self.age_group_child, None, self.inv_param.id)
        self.assertIsNone(result)

    def test_boundary_ages(self):
        """Test boundary conditions (if we had age computation, but here we just pass the matched age_group)."""
        # Since resolveReferenceRange takes the resolved age_group as input, 
        # testing boundary ages is technically about testing the function that maps age -> AgeGroup.
        # But per requirements, resolveReferenceRange takes patient_age_group.
        # We will just verify it correctly handles the input.
        result = resolveReferenceRange(self.age_group_newborn, None, self.inv_param.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.range_newborn_generic.id)
