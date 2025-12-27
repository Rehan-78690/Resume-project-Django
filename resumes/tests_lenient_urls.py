from django.test import TestCase
from rest_framework.exceptions import ValidationError
from resumes.serializers import LenientURLField, TemplateSerializer

class LenientURLFieldTests(TestCase):
    def setUp(self):
        # Create field with allow_blank=True for standard testing
        self.field = LenientURLField(allow_blank=True, required=False)

    def test_complete_url_remains_unchanged(self):
        """Test that a valid URL with scheme is preserved."""
        url = "https://example.com/profile"
        self.assertEqual(self.field.run_validation(url), url)
        
        url_http = "http://example.com"
        self.assertEqual(self.field.run_validation(url_http), url_http)

    def test_missing_scheme_adds_https(self):
        """Test that a clean domain gets https:// prepended."""
        url = "example.com"
        expected = "https://example.com"
        self.assertEqual(self.field.run_validation(url), expected)

    def test_missing_scheme_with_start_path(self):
        """Test that a path without scheme gets https:// prepended."""
        url = "linkedin.com/in/jdoe"
        expected = "https://linkedin.com/in/jdoe"
        self.assertEqual(self.field.run_validation(url), expected)

    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed before normalization."""
        url = "   example.com   "
        expected = "https://example.com"
        self.assertEqual(self.field.run_validation(url), expected)

    def test_empty_string_allowed(self):
        """Test that empty strings are accepted if allow_blank=True."""
        self.assertEqual(self.field.run_validation(""), "")
        # Note: self.field in setUp is NOT nullable, so run_validation(None) raises ValidationError by DRF's default behavior,
        # skipping to_internal_value completely.
        # We test explicit null behavior in test_allow_null_behavior.

    def test_allow_null_behavior(self):
        """Test explicit allow_null behavior."""
        field = LenientURLField(allow_null=True)
        self.assertIsNone(field.run_validation(None))

    def test_invalid_url_raises_error(self):
        """Test that essentially invalid strings still fail Django's URLValidator."""
        # "not a url" becomes "https://not a url", which fails validation due to spaces
        with self.assertRaises(ValidationError):
            self.field.run_validation("  not a url  ")
            
        # Test a scheme-like string that isn't http/https (should not be touched, then fail if not a valid URL)
        # But wait, our logic ONLY adds https if http/s is missing.
        # If I pas "ftp://foo", it keeps "ftp://foo". Use URLField defaults (usually http/s only unless configured).
        # Let's verify standard URLField behavior isn't broken for other schemes if they were allowed, 
        # but standard Django URLValidator usually defaults to http/https/ftp/ftps.
        # Let's stick to the user case: ensure "random string" fails.
        with self.assertRaises(ValidationError):
            self.field.run_validation("https://")  # Just scheme is invalid
            
    def test_scheme_logic_edge_cases(self):
        """Test logic for adding scheme."""
        # "example.com" -> https://example.com
        self.assertEqual(self.field.run_validation("example.com"), "https://example.com")
        
        # "www.example.com" -> https://www.example.com
        self.assertEqual(self.field.run_validation("www.example.com"), "https://www.example.com")

class TemplateSerializerPhotoTests(TestCase):
    def test_validate_definition_allows_show_photo(self):
        """Test that 'show_photo' is allowed in section config."""
        serializer = TemplateSerializer()
        valid_definition = {
            "schema_version": 1,
            "layout": {"type": "single-column"},
            "style": {},
            "sections": {
                "personal_info": {
                    "visible": True,
                    "order": 0,
                    "area": "header",
                    "show_photo": True  # The new field
                }
            }
        }
        # Should not raise
        result = serializer.validate_definition(valid_definition)
        self.assertEqual(result, valid_definition)

    def test_validate_definition_rejects_bad_show_photo_type(self):
        """Test that strict type checking works for show_photo."""
        serializer = TemplateSerializer()
        invalid_definition = {
            "schema_version": 1,
            "layout": {"type": "single-column"},
            "style": {},
            "sections": {
                "personal_info": {
                    "show_photo": "yes"  # Invalid, must be bool
                }
            }
        }
        with self.assertRaises(ValidationError) as cm:
            serializer.validate_definition(invalid_definition)
        self.assertIn("must be bool", str(cm.exception))

    def test_validate_definition_legacy_unchanged(self):
        """Test that definitions without the new key are still valid."""
        serializer = TemplateSerializer()
        legacy_definition = {
            "schema_version": 1,
            "layout": {"type": "single-column"},
            "style": {},
            "sections": {
                "personal_info": {
                    "visible": True
                }
            }
        }
        # Should not raise
        serializer.validate_definition(legacy_definition)
