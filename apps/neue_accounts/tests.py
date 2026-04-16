from django.test import TestCase
from django.urls import reverse

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
        cls.user = NeueUser.objects.create_user(email="test@test.com", password="Xx_testpassword_xX123")
        cls.login_url = reverse("neue_accounts:login")

    def test_root_is_login_protected(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)
        self.assertIn('next=', response.url)

        response = self.client.post(self.login_url, {
            'email': 'test@test.com',
            'password': 'Xx_testpassword_xX123'
            }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.request['PATH_INFO'], reverse('journal:home'))

    def test_login_with_valid_credentials(self):
        response = self.client.post(self.login_url, {
            'email': 'test@test.com',
            'password': 'Xx_testpassword_xX123'
        })

        self.assertEqual(response.status_code, 302)

        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)

    def test_login_with_invalid_credentials(self):
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })

        self.assertEqual(response.status_code, 200)

        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)

        self.assertContains(response, 'Invalid email or password.')


class LogoutTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = NeueUser.objects.create_user(email="test@test.com", password="Xx_testpassword_xX123")
        cls.logout_url = reverse('neue_accounts:logout')

    def test_logout(self):
        self.client.login(email='test@test.com', password='Xx_testpassword_xX123')

        response = self.client.get(reverse('journal:home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('journal:home'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

class ProtectedViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = NeueUser.objects.create_user(email="test@test.com", password="Xx_testpassword_xX123")
        cls.protected_url = reverse('journal:home')

    def test_protected_view_redirects_anonymous_user(self):
        response = self.client.get(self.protected_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)

    def test_protected_view_accessible_to_authenticated_user(self):
        self.client.login(email="test@test.com", password='Xx_testpassword_xX123')

        response = self.client.get(self.protected_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'datepicker')

class RegisterTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register_url = reverse("neue_accounts:register")
        return super().setUpClass()

    def test_signup_with_valid_data(self):
        response = self.client.post(self.register_url, {
            'email': 'test@test.com',
            'password': 'Xx_testpassword_xX123',
            'confirmPassword': "Xx_testpassword_xX123"
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(NeueUser.objects.filter(email="test@test.com").exists())

        user = NeueUser.objects.get(email="test@test.com")
        self.assertTrue(user.is_authenticated)

    def test_signup_with_mismatched_passwords(self):
        response = self.client.post(self.register_url, {
            'email': 'test@test.com',
            'password': 'Xx_testpassword_xX123',
            'confirmPassword': "AHHHHHHHH123ahhhhhhhh"
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(NeueUser.objects.filter(email="test@test.com").exists())

        self.assertContains(response, "Passwords do not match.")

    def test_signup_with_existing_email(self):
        NeueUser.objects.create_user(email="test2@test.com", password="123complexpassword")

        response = self.client.post(self.register_url, {
            'email': 'test2@test.com',
            'password': 'evenmorecomplexpassword123',
            'confirmPassword': 'evenmorecomplexpassword123'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")
