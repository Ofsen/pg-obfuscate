"""Faker-based obfuscation strategy."""

from typing import Any

from faker import Faker

from pg_obfuscate.strategies.base import BaseStrategy


class FakeStrategy(BaseStrategy):
    """Faker-based obfuscation strategy with typed outputs."""

    # Mapping of type names to Faker method names
    TYPE_MAPPING = {
        "email": "email",
        "name": "name",
        "first_name": "first_name",
        "last_name": "last_name",
        "phone": "phone_number",
        "address": "address",
        "company": "company",
        "text": "text",
        "city": "city",
        "country": "country",
        "postcode": "postcode",
        "street_address": "street_address",
        "job": "job",
        "url": "url",
        "username": "user_name",
        "uuid": "uuid4",
        "date": "date",
        "datetime": "date_time",
        # Numeric types
        "int": "random_int",
        "number": "random_int",
        "float": "pyfloat",
        "decimal": "pydecimal",
        "price": "pricetag",
    }
    
    # Types that should not be converted to string
    NUMERIC_TYPES = {"int", "number", "float", "decimal"}

    def __init__(self, fake_type: str):
        """Initialize with a specific fake type.
        
        Args:
            fake_type: Type of fake data (email, name, phone, etc.)
            
        Raises:
            ValueError: If fake_type is not supported
        """
        if fake_type not in self.TYPE_MAPPING:
            supported = ", ".join(sorted(self.TYPE_MAPPING.keys()))
            raise ValueError(
                f"Unsupported fake type '{fake_type}'. Supported: {supported}"
            )
        self.fake_type = fake_type
        self.faker_method = self.TYPE_MAPPING[fake_type]

    def obfuscate(self, value: Any, seed: int) -> Any:
        """Generate fake value seeded by original.
        
        Args:
            value: Original value (used for seeding and scale matching)
            seed: Computed seed for determinism
            
        Returns:
            Fake value of the configured type
        """
        if value is None:
            return None
        
        # Create Faker instance with specific seed for determinism
        fake = Faker()
        Faker.seed(seed)
        
        # Handle numeric types - match original value's scale
        if self.fake_type in self.NUMERIC_TYPES:
            return self._generate_matching_number(fake, value)
        
        # Get the faker method and call it
        method = getattr(fake, self.faker_method)
        result = method()
        
        return str(result)

    def _generate_matching_number(self, fake: Faker, original: Any) -> Any:
        """Generate a fake number matching the original's scale.
        
        Args:
            fake: Faker instance (already seeded)
            original: Original numeric value
            
        Returns:
            Fake number with similar magnitude and decimal places
        """
        from decimal import Decimal
        
        # Convert to string to analyze structure
        str_val = str(original)
        
        # Determine decimal places
        if "." in str_val:
            integer_part, decimal_part = str_val.split(".", 1)
            decimal_places = len(decimal_part)
        else:
            integer_part = str_val.lstrip("-")
            decimal_places = 0
        
        # Determine magnitude (number of digits in integer part)
        integer_part = integer_part.lstrip("-")
        num_digits = len(integer_part) if integer_part and integer_part != "0" else 1
        
        # Calculate range based on magnitude
        max_val = 10 ** num_digits - 1
        min_val = 10 ** (num_digits - 1) if num_digits > 1 else 0
        
        if self.fake_type in ("int", "number"):
            return fake.random_int(min=min_val, max=max_val)
        elif self.fake_type == "float":
            result = fake.pyfloat(
                min_value=float(min_val),
                max_value=float(max_val),
                right_digits=decimal_places,
            )
            return result
        elif self.fake_type == "decimal":
            result = fake.pydecimal(
                min_value=min_val,
                max_value=max_val,
                right_digits=decimal_places,
            )
            return result
        
        return original  # Fallback
