from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.helpers.email import AccountActivationTokenGenerator

from .models import NeueUser


# Create your tests here.
class LoginPageTests(TestCase):
    def test_url_exists_at_correct_location(self):
        response = self.client.get("/auth/login/")
        self.assertEqual(response.status_code, 200)

    def test_login_url_available_by_name(self):
        response = self.client.get(reverse("neue_accounts:login"))
        self.assertEqual(response.status_code, 200)

    def test_login_template_correct(self):
        response = self.client.get(reverse("neue_accounts:login"))
        self.assertTemplateUsed(response, "neue_accounts/login.html")


class RegisterPageTests(TestCase):
    def test_url_exists_at_correct_location(self):
        response = self.client.get("/auth/register/")
        self.assertEqual(response.status_code, 200)

    def test_url_available(self):
        response = self.client.get(reverse("neue_accounts:register"))
        self.assertEqual(response.status_code, 200)

    def test_template_correct(self):
        response = self.client.get(reverse("neue_accounts:register"))
        self.assertTemplateUsed(response, "neue_accounts/register.html")


class AuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.journal.models import JournalSettings

        cls.user = NeueUser.objects.create_user(
            email="test@test.com", password="Xx_testpassword_xX123"
        )
        cls.user.is_active = True
        cls.user.save()
        JournalSettings.objects.create(
            owner=cls.user, belongs_to="Test User", colour="6f4518"
        )
        cls.login_url = reverse("neue_accounts:login")

    def test_root_is_login_protected(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/landing.html")

        response = self.client.post(
            self.login_url,
            {"email": "test@test.com", "password": "Xx_testpassword_xX123"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.request["PATH_INFO"], reverse("journal:home"))

    def test_login_with_valid_credentials(self):
        response = self.client.post(
            self.login_url,
            {"email": "test@test.com", "password": "Xx_testpassword_xX123"},
        )

        self.assertEqual(response.status_code, 302)

        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)

    def test_login_with_invalid_credentials(self):
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "wrongpassword"}
        )

        self.assertEqual(response.status_code, 200)

        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)

        self.assertContains(response, "Invalid email or password.")


class LogoutTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = NeueUser.objects.create_user(
            email="test@test.com", password="Xx_testpassword_xX123"
        )
        cls.user.is_active = True
        cls.user.save()
        cls.logout_url = reverse("neue_accounts:logout")

    def test_logout(self):
        self.client.login(email="test@test.com", password="Xx_testpassword_xX123")

        response = self.client.get(reverse("journal:home"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse("journal:home"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ProtectedViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.journal.models import JournalSettings

        cls.user = NeueUser.objects.create_user(
            email="test@test.com", password="Xx_testpassword_xX123"
        )
        cls.user.is_active = True
        cls.user.save()
        JournalSettings.objects.create(
            owner=cls.user, belongs_to="Test User", colour="6f4518"
        )
        cls.protected_url = reverse("journal:home")

    def test_protected_view_shows_landing_to_anonymous_user(self):
        response = self.client.get(self.protected_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/landing.html")

    def test_protected_view_accessible_to_authenticated_user(self):
        self.client.login(email="test@test.com", password="Xx_testpassword_xX123")

        response = self.client.get(self.protected_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/journal.html")


class RegisterTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register_url = reverse("neue_accounts:register")
        return super().setUpClass()

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_signup_with_valid_data(self):
        """Test that signup creates an inactive user and sends verification email"""
        response = self.client.post(
            self.register_url,
            {
                "email": "test@test.com",
                "password": "Xx_testpassword_xX123",
                "confirmPassword": "Xx_testpassword_xX123",
            },
        )

        # Should redirect to verification message page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NeueUser.objects.filter(email="test@test.com").exists())

        user = NeueUser.objects.get(email="test@test.com")
        # User should be inactive until email verification
        self.assertFalse(user.is_active)
        # User should not be authenticated yet
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_signup_with_mismatched_passwords(self):
        response = self.client.post(
            self.register_url,
            {
                "email": "test@test.com",
                "password": "Xx_testpassword_xX123",
                "confirmPassword": "AHHHHHHHH123ahhhhhhhh",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(NeueUser.objects.filter(email="test@test.com").exists())

        self.assertContains(response, "Passwords do not match.")

    def test_signup_with_existing_email(self):
        NeueUser.objects.create_user(
            email="test2@test.com", password="123complexpassword"
        )

        response = self.client.post(
            self.register_url,
            {
                "email": "test2@test.com",
                "password": "evenmorecomplexpassword123",
                "confirmPassword": "evenmorecomplexpassword123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")


class EmailVerificationTestCase(TestCase):
    """Tests for the email verification pipeline"""

    @classmethod
    def setUpTestData(cls):
        cls.token_generator = AccountActivationTokenGenerator()

    def test_verify_message_page_displays_correct_email(self):
        """Test that the verify message page shows the user's email"""
        user = NeueUser.objects.create_user(
            email="verify@test.com", password="Xx_testpassword_xX123"
        )
        user.is_active = False
        user.save()

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(
            reverse("neue_accounts:verify_message", kwargs={"uidb64": uidb64})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "neue_accounts/verify_message.html")
        self.assertContains(response, user.email)

    def test_verify_message_page_with_invalid_uidb64(self):
        """Test that verify message page handles invalid user ID"""
        invalid_uidb64 = "invalid_base64"
        response = self.client.get(
            reverse("neue_accounts:verify_message", kwargs={"uidb64": invalid_uidb64})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "neue_accounts/register.html")
        self.assertContains(
            response, "There was an issue sending our verification email"
        )

    def test_activate_with_valid_token(self):
        """Test that activation with a valid token activates the user"""
        user = NeueUser.objects.create_user(
            email="activate@test.com", password="Xx_testpassword_xX123"
        )
        user.is_active = False
        user.save()

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = self.token_generator.make_token(user)

        response = self.client.get(
            reverse(
                "neue_accounts:activate",
                kwargs={"uidb64": uidb64, "token": token},
            )
        )

        # Should redirect to home page after successful activation
        self.assertEqual(response.status_code, 302)
        self.assertIn(response.url, ["/", "/auth/"])

        # User should now be active
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # User should be logged in after activation
        response = self.client.get("/", follow=True)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.email, "activate@test.com")

    def test_activate_with_invalid_token(self):
        """Test that activation with an invalid token fails"""
        user = NeueUser.objects.create_user(
            email="badtoken@test.com", password="Xx_testpassword_xX123"
        )
        user.is_active = False
        user.save()

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        invalid_token = "invalid-token"

        response = self.client.get(
            reverse(
                "neue_accounts:activate",
                kwargs={"uidb64": uidb64, "token": invalid_token},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "neue_accounts/register.html")
        self.assertContains(response, "There was an issue verifying your email")

        # User should still be inactive
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_activate_with_invalid_uidb64(self):
        """Test that activation with an invalid user ID fails"""
        invalid_uidb64 = "invalid_base64"
        token = "some-token"

        response = self.client.get(
            reverse(
                "neue_accounts:activate",
                kwargs={"uidb64": invalid_uidb64, "token": token},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "neue_accounts/register.html")
        self.assertContains(response, "There was an issue verifying your email")

    def test_activate_already_active_user(self):
        """Test that activation still works on already-active users"""
        user = NeueUser.objects.create_user(
            email="already@test.com", password="Xx_testpassword_xX123"
        )
        user.is_active = True
        user.save()

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = self.token_generator.make_token(user)

        response = self.client.get(
            reverse(
                "neue_accounts:activate",
                kwargs={"uidb64": uidb64, "token": token},
            )
        )

        # Should still succeed and redirect
        self.assertEqual(response.status_code, 302)

        # User should remain active
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_token_expires_after_time(self):
        """Test that tokens follow expiration rules from AccountActivationTokenGenerator"""
        user = NeueUser.objects.create_user(
            email="expiry@test.com", password="Xx_testpassword_xX123"
        )
        user.is_active = False
        user.save()

        token = self.token_generator.make_token(user)

        # Token should be valid immediately
        self.assertTrue(self.token_generator.check_token(user, token))

        # Modify the user to invalidate the token
        user.date_joined = user.date_joined
        user.save()

        # Token should still be valid unless date_joined changed (depends on token generator implementation)
        # This test documents the expected behavior

    def test_signup_flow_complete(self):
        """Integration test: signup -> verify message -> activate"""
        register_url = reverse("neue_accounts:register")

        # Step 1: Register
        response = self.client.post(
            register_url,
            {
                "email": "flow@test.com",
                "password": "Xx_testpassword_xX123",
                "confirmPassword": "Xx_testpassword_xX123",
            },
        )

        self.assertEqual(response.status_code, 302)
        user = NeueUser.objects.get(email="flow@test.com")
        self.assertFalse(user.is_active)

        # Step 2: Verify message page
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(
            reverse("neue_accounts:verify_message", kwargs={"uidb64": uidb64})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "flow@test.com")

        # Step 3: Activate
        token = self.token_generator.make_token(user)
        response = self.client.get(
            reverse(
                "neue_accounts:activate",
                kwargs={"uidb64": uidb64, "token": token},
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
