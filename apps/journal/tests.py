from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse

from .models import Entry, Mood
from ..neue_accounts.models import NeueUser


class JournalPageTests(TestCase):
    def setUp(self):
        self.user = NeueUser.objects.create_user(email="test@test.com", password="strongpassword123")
        self.client.force_login(self.user)

    def test_url_exists_at_correct_location(self):
        # Check that an authenticated user can access the route page and it renders the journal template
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/journal.html")

class EntryCreationTests(TestCase):
    def setUp(self):
        self.user = NeueUser.objects.create_user(email="test@test.com", password="strongpassword123")
        self.client.force_login(self.user)

    def test_home_view_creates_today_entry(self):
        today = datetime.today()

        # Create an entry from the home route by getting "/"
        response = self.client.get("/")
        dateStr = today.strftime("%d/%m/%Y")

        # Verify the journal template was used and it contains the correct date
        self.assertTemplateUsed(response, "journal/journal.html")
        self.assertContains(response, dateStr)

        # Verify the entry object was created in the db
        entry = Entry.objects.filter(owner=self.user, date=today).first()
        self.assertEqual(entry.owner, self.user)

    def test_entry_date_page_creates_entry(self):
        # Create an entry from the "/entry" route
        date = datetime(2025, 10, 14)
        response = self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))
        entry = Entry.objects.filter(owner=self.user, date=date).first()

        # Verify it creates the entry in the db and responds properly
        self.assertEqual(response.status_code, 200)
        self.assertEqual(entry.owner, self.user)
        self.assertEqual(entry.date, date.date())

class EntryEditingTests(TestCase):
    def setUp(self):
        self.user = NeueUser.objects.create_user(email="test@test.com", password="strongpassword123")
        self.client.force_login(self.user)

    def test_save_entry_encrypts_content(self):
        today = datetime.today()

        # Create an entry first by accessing the home page
        self.client.get("/")

        # Get today's entry
        entry = Entry.objects.filter(owner=self.user, date=today).first()
        self.assertIsNotNone(entry)

        # Save content via the save endpoint
        test_content = b"Test journal entry content"
        save_url = reverse("journal:save-entry", args=[today.strftime("%d"), today.strftime("%m"), today.year])
        response = self.client.post(save_url, data=test_content, content_type='application/octet-stream')

        # Refresh entry from database
        entry.refresh_from_db()

        # Verify the saved content is NOT equal to plain text (i.e., it's encrypted)
        self.assertNotEqual(bytes(entry.content), test_content)
        self.assertEqual(response.status_code, 200)

    def test_load_entry_decrypts_content(self):
        today = datetime.today()

        # Create an entry first by accessing the home page
        self.client.get("/")

        # Get today's entry
        entry = Entry.objects.filter(owner=self.user, date=today).first()
        self.assertIsNotNone(entry)

        # Save content via the save endpoint
        test_content = b"Test journal entry content for decryption"
        save_url = reverse("journal:save-entry", args=[today.strftime("%d"), today.strftime("%m"), today.year])
        self.client.post(save_url, data=test_content, content_type='application/octet-stream')

        # Load the entry back
        load_url = reverse("journal:load-entry", args=[today.strftime("%d"), today.strftime("%m"), today.year])
        response = self.client.get(load_url)

        # Verify the returned content matches the original saved content
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test journal entry content for decryption")

class EntryDeletionTests(TestCase):
    def setUp(self):
        self.user = NeueUser.objects.create_user(email="test@test.com", password="strongpassword123")
        self.client.force_login(self.user)

    def test_delete_entry_removes_from_db(self):
        date = datetime(2025, 10, 14)
        self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))

        entry = Entry.objects.filter(owner=self.user, date=date).first()
        self.assertIsNotNone(entry)

        delete_url = reverse("journal:delete-entry", args=[14, 10, 2025])
        self.client.delete(delete_url)

        entry_exists = Entry.objects.filter(owner=self.user, date=date).exists()
        self.assertFalse(entry_exists)

    def test_delete_redirects_to_previous_entry(self):

        self.client.get(reverse("journal:load-entry", args=[15, 10, 2025]))
        self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))

        delete_url = reverse("journal:delete-entry", args=[15, 10, 2025])
        response = self.client.delete(delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("journal:load-entry", args=[14, 10, 2025]))

    def test_delete_oldest_redirects_to_home(self):
        self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))

        delete_url = reverse("journal:delete-entry", args=[14, 10, 2025])
        response = self.client.delete(delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/")

class SecurityTests(TestCase):
    def setUp(self):
        self.user = NeueUser.objects.create_user(email="test@test.com", password="strongpassword123")
        self.client.force_login(self.user)

    def test_user_cannot_access_other_users_entries(self):
        date = datetime(2025, 10, 14)
        self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))

        # Save some content as User A
        test_content = b"Private content that should not be accessible"
        save_url = reverse("journal:save-entry", args=[14, 10, 2025])
        self.client.post(save_url, data=test_content, content_type='application/octet-stream')

        # Create a second user and try to access the first user's entry
        other_user = NeueUser.objects.create_user(email="other@test.com", password="strongpassword123")
        self.client.force_login(other_user)

        # Try to load the entry - should get a new empty entry for User B
        load_url = reverse("journal:load-entry", args=[14, 10, 2025])
        response = self.client.get(load_url)

        # Verify the response does not contain User A's private content
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Private content that should not be accessible")

        # Verify User B gets their own entry, not User A's
        entry_for_other = Entry.objects.filter(owner=other_user, date=date).first()
        self.assertIsNotNone(entry_for_other)
        self.assertNotEqual(bytes(entry_for_other.content), test_content)

class MoodCreationTests(TestCase):
    def setUp(self):
        self.user = NeueUser.objects.create_user(email="test@test.com", password="strongpassword123")
        self.client.force_login(self.user)

    def test_set_mood_creates_mood_entry(self):
        date = datetime(2025, 10, 14)
        self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))

        # Set a mood for that date
        mood_url = reverse("journal:set-mood", args=[14, 10, 2025, "happy"])
        response = self.client.post(mood_url)

        # Verify the mood was created
        entry = Entry.objects.get(owner=self.user, date=date.date())
        mood = Mood.objects.get(owner=self.user, entry=entry)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mood.happiness, Decimal('0.5'))

    def test_set_mood_updates_existing_mood(self):
        date = datetime(2025, 10, 14)
        self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))
        entry = Entry.objects.get(owner=self.user, date=date.date())

        # Set initial mood
        mood_url = reverse("journal:set-mood", args=[14, 10, 2025, "sad"])
        self.client.post(mood_url)

        initial_mood = Mood.objects.get(owner=self.user, entry=entry)
        self.assertEqual(initial_mood.happiness, Decimal('-0.5'))

        # Update to a different mood
        mood_url = reverse("journal:set-mood", args=[14, 10, 2025, "very-happy"])
        self.client.post(mood_url)

        # Verify only one mood entry exists and it was updated
        mood_count = Mood.objects.filter(owner=self.user, entry=entry).count()
        self.assertEqual(mood_count, 1)

        updated_mood = Mood.objects.get(owner=self.user, entry=entry)
        self.assertEqual(updated_mood.happiness, Decimal('1.0'))

    def test_set_mood_requires_post_method(self):
        mood_url = reverse("journal:set-mood", args=[14, 10, 2025, "happy"])
        response = self.client.get(mood_url)

        self.assertEqual(response.status_code, 405)

class MoodRetrievalTests(TestCase):
    def setUp(self):
        self.user = NeueUser.objects.create_user(email="test@test.com", password="strongpassword123")
        self.client.force_login(self.user)

    def test_mood_data_in_context(self):
        response = self.client.get("/")

        # Verify all mood time period keys are in the response context
        self.assertIn('moods_week', response.context)
        self.assertIn('moods_month', response.context)
        self.assertIn('moods_year', response.context)
        self.assertIn('moods_lifetime', response.context)

    def test_fetch_mood_week(self):
        date = datetime(2025, 10, 14)
        # Create an entry through the proper route
        self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))
        entry = Entry.objects.get(owner=self.user, date=date.date())

        # Add a mood to it
        Mood.objects.create(
            owner=self.user,
            entry=entry,
            happiness=Decimal('0.5')
        )

        response = self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))

        # Verify moods are in context
        self.assertIn('moods_week', response.context)
        self.assertIsNotNone(response.context['moods_week'])

class MoodSecurityTests(TestCase):
    def setUp(self):
        self.user1 = NeueUser.objects.create_user(email="user1@test.com", password="strongpassword123")
        self.user2 = NeueUser.objects.create_user(email="user2@test.com", password="strongpassword123")

    def test_user_cannot_see_other_users_moods(self):
        date = datetime(2025, 10, 14)
        # Create entry for user1
        self.client.force_login(self.user1)
        self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))

        entry = Entry.objects.get(owner=self.user1, date=date.date())
        Mood.objects.create(
            owner=self.user1,
            entry=entry,
            happiness=Decimal('1.0')
        )

        # Login as user2
        self.client.force_login(self.user2)
        response = self.client.get(reverse("journal:load-entry", args=[14, 10, 2025]))

        # Verify user2 has no moods from user1
        user2_moods = Mood.objects.filter(owner=self.user2).count()
        self.assertEqual(user2_moods, 0)
