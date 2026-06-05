import io
import json
from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from ..neue_accounts.models import NeueUser
from .models import (
    Entry,
    JournalSettings,
    OwnedPack,
    Photo,
    Sticker,
    StickerPack,
    StickerPosition,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_user(email="test@test.com", password="strongpassword123"):
    return NeueUser.objects.create_user(email=email, password=password)


def make_image(name="photo.jpg", fmt="JPEG"):
    """Return a minimal valid image as a SimpleUploadedFile."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(255, 0, 0)).save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


def make_image_of_size(name="large.jpg", size_bytes=5 * 1024 * 1024):
    """Return a SimpleUploadedFile with exactly *size_bytes* of dummy data."""
    return SimpleUploadedFile(
        name,
        b"\x00" * size_bytes,
        content_type="image/jpeg",
    )


def create_entry(client, content="A great day", entry_type="milestone", images=None):
    data = {"content": content, "entry_type": entry_type}
    if images:
        data["images"] = images
    return client.post(reverse("journal:create-entry"), data=data, format="multipart")


# ---------------------------------------------------------------------------
# Home View
# ---------------------------------------------------------------------------


class HomeViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        JournalSettings.objects.create(
            owner=self.user, belongs_to="Test User", colour="6f4518"
        )

    def test_authenticated_user_sees_journal_template(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("journal:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/journal.html")

    def test_anonymous_user_sees_landing_template(self):
        response = self.client.get(reverse("journal:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/landing.html")

    def test_home_view_get_does_not_create_entry(self):
        self.client.force_login(self.user)
        self.client.get(reverse("journal:home"))
        self.assertEqual(Entry.objects.filter(owner=self.user).count(), 0)


# ---------------------------------------------------------------------------
# Authentication on create_entry
# ---------------------------------------------------------------------------


class CreateEntryAuthTests(TestCase):
    def test_anonymous_post_redirects_to_login(self):
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "hello", "entry_type": "milestone"},
        )
        self.assertIn(response.status_code, [301, 302])
        self.assertIn("/auth/login", response["Location"])

    def test_anonymous_get_redirects_to_login(self):
        response = self.client.get(reverse("journal:create-entry"))
        self.assertIn(response.status_code, [301, 302])
        self.assertIn("/auth/login", response["Location"])


# ---------------------------------------------------------------------------
# create_entry — HTTP method guard
# ---------------------------------------------------------------------------


class CreateEntryMethodTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_get_returns_405(self):
        response = self.client.get(reverse("journal:create-entry"))
        self.assertEqual(response.status_code, 405)

    def test_put_returns_405(self):
        response = self.client.put(reverse("journal:create-entry"))
        self.assertEqual(response.status_code, 405)

    def test_patch_returns_405(self):
        response = self.client.patch(reverse("journal:create-entry"))
        self.assertEqual(response.status_code, 405)

    def test_delete_returns_405(self):
        response = self.client.delete(reverse("journal:create-entry"))
        self.assertEqual(response.status_code, 405)


# ---------------------------------------------------------------------------
# create_entry — Input validation
# ---------------------------------------------------------------------------


class CreateEntryValidationTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_missing_content_returns_400(self):
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"entry_type": "milestone"},
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_entry_type_returns_400(self):
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "Some text"},
        )
        self.assertEqual(response.status_code, 400)

    def test_whitespace_only_content_returns_400(self):
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "   ", "entry_type": "milestone"},
        )
        self.assertEqual(response.status_code, 400)

    def test_whitespace_only_entry_type_returns_400(self):
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "Some text", "entry_type": "   "},
        )
        self.assertEqual(response.status_code, 400)

    def test_both_fields_missing_returns_400(self):
        response = self.client.post(reverse("journal:create-entry"), data={})
        self.assertEqual(response.status_code, 400)

    def test_error_response_contains_informative_message(self):
        response = self.client.post(reverse("journal:create-entry"), data={})
        self.assertIn(b"content", response.content.lower())

    def test_four_images_returns_400(self):
        images = [make_image(f"{i}.jpg") for i in range(4)]
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "text", "entry_type": "milestone", "images": images},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_four_images_error_message_mentions_limit(self):
        images = [make_image(f"{i}.jpg") for i in range(4)]
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "text", "entry_type": "milestone", "images": images},
            format="multipart",
        )
        self.assertIn(b"3", response.content)


# ---------------------------------------------------------------------------
# create_entry — Image size limit (5MB)
# ---------------------------------------------------------------------------


class CreateEntryImageSizeTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_exactly_5mb_image_is_accepted(self):
        """Boundary test: 5 * 1024 * 1024 bytes should pass."""
        image = make_image_of_size("exactly5mb.jpg", size_bytes=5 * 1024 * 1024)
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "text", "entry_type": "milestone", "images": [image]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)

    def test_5mb_plus_one_byte_image_is_rejected(self):
        """Boundary test: 5 * 1024 * 1024 + 1 bytes should fail."""
        image = make_image_of_size("too_big.jpg", size_bytes=5 * 1024 * 1024 + 1)
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "text", "entry_type": "milestone", "images": [image]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_oversized_image_error_message_mentions_limit(self):
        image = make_image_of_size("too_big.jpg", size_bytes=5 * 1024 * 1024 + 1)
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "text", "entry_type": "milestone", "images": [image]},
            format="multipart",
        )
        self.assertIn(b"5MB", response.content)

    def test_oversized_image_error_message_mentions_filename(self):
        image = make_image_of_size("my_huge_photo.jpg", size_bytes=5 * 1024 * 1024 + 1)
        response = self.client.post(
            reverse("journal:create-entry"),
            data={"content": "text", "entry_type": "milestone", "images": [image]},
            format="multipart",
        )
        self.assertIn(b"my_huge_photo.jpg", response.content)

    def test_multiple_images_one_oversized_is_rejected(self):
        """If any image exceeds the limit, the whole request fails."""
        small = make_image("small.jpg")
        large = make_image_of_size("large.jpg", size_bytes=5 * 1024 * 1024 + 1)
        response = self.client.post(
            reverse("journal:create-entry"),
            data={
                "content": "text",
                "entry_type": "milestone",
                "images": [small, large],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_multiple_images_all_within_limit_are_accepted(self):
        images = [make_image_of_size(f"img{i}.jpg", size_bytes=1024) for i in range(3)]
        response = self.client.post(
            reverse("journal:create-entry"),
            data={
                "content": "text",
                "entry_type": "milestone",
                "images": images,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# create_entry — Successful creation
# ---------------------------------------------------------------------------


class CreateEntrySuccessTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_valid_post_returns_200(self):
        response = create_entry(self.client)
        self.assertEqual(response.status_code, 200)

    def test_valid_post_creates_entry_in_db(self):
        create_entry(self.client)
        self.assertEqual(Entry.objects.filter(owner=self.user).count(), 1)

    def test_entry_owner_is_request_user(self):
        create_entry(self.client)
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.owner, self.user)

    def test_entry_date_is_today(self):
        create_entry(self.client)
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.date, datetime.today().date())

    def test_milestone_type_stored_correctly(self):
        create_entry(self.client, entry_type="milestone")
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.type, Entry.Type.MILESTONE)

    def test_lesson_type_stored_correctly(self):
        create_entry(self.client, entry_type="lesson")
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.type, Entry.Type.LESSON)

    def test_event_type_stored_correctly(self):
        create_entry(self.client, entry_type="event")
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.type, Entry.Type.EVENT)

    def test_content_is_encrypted_at_rest(self):
        plaintext = "My secret diary entry"
        create_entry(self.client, content=plaintext)
        entry = Entry.objects.get(owner=self.user)
        self.assertNotEqual(bytes(entry.content), plaintext.encode())

    def test_content_field_is_non_empty(self):
        create_entry(self.client, content="Something")
        entry = Entry.objects.get(owner=self.user)
        self.assertGreater(len(bytes(entry.content)), 0)

    def test_post_with_no_images_creates_no_photos(self):
        create_entry(self.client)
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.photos.count(), 0)

    def test_post_with_one_image_creates_one_photo(self):
        create_entry(self.client, images=[make_image()])
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.photos.count(), 1)

    def test_post_with_two_images_creates_two_photos(self):
        create_entry(self.client, images=[make_image("a.jpg"), make_image("b.jpg")])
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.photos.count(), 2)

    def test_post_with_three_images_creates_three_photos(self):
        images = [make_image(f"{i}.jpg") for i in range(3)]
        create_entry(self.client, images=images)
        entry = Entry.objects.get(owner=self.user)
        self.assertEqual(entry.photos.count(), 3)

    def test_photos_are_linked_to_correct_entry(self):
        create_entry(self.client, images=[make_image()])
        entry = Entry.objects.get(owner=self.user)
        photo = entry.photos.first()
        self.assertEqual(photo.entry, entry)

    def test_multiple_posts_create_multiple_entries(self):
        create_entry(self.client, content="First")
        create_entry(self.client, content="Second")
        self.assertEqual(Entry.objects.filter(owner=self.user).count(), 2)


# ---------------------------------------------------------------------------
# create_entry — Encryption
# ---------------------------------------------------------------------------


class EncryptionTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_plaintext_not_stored_verbatim(self):
        plaintext = "Top secret thoughts"
        create_entry(self.client, content=plaintext)
        entry = Entry.objects.get(owner=self.user)
        self.assertNotIn(plaintext.encode(), bytes(entry.content))

    def test_two_users_same_content_produce_different_ciphertext(self):
        plaintext = "Identical content"
        create_entry(self.client, content=plaintext)
        ciphertext_a = bytes(Entry.objects.get(owner=self.user).content)

        other = create_user("other@test.com")
        self.client.force_login(other)
        create_entry(self.client, content=plaintext)
        ciphertext_b = bytes(Entry.objects.get(owner=other).content)

        self.assertNotEqual(ciphertext_a, ciphertext_b)


# ---------------------------------------------------------------------------
# Photo model
# ---------------------------------------------------------------------------


class PhotoModelTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.entry = Entry.objects.create(
            owner=self.user,
            content=b"encrypted",
            type=Entry.Type.MILESTONE,
            date=datetime.today().date(),
        )

    def test_first_photo_saves_successfully(self):
        photo = Photo(entry=self.entry, image=make_image())
        photo.save()
        self.assertIsNotNone(photo.pk)

    def test_second_photo_saves_successfully(self):
        Photo(entry=self.entry, image=make_image("a.jpg")).save()
        Photo(entry=self.entry, image=make_image("b.jpg")).save()
        self.assertEqual(self.entry.photos.count(), 2)

    def test_third_photo_saves_successfully(self):
        for i in range(3):
            Photo(entry=self.entry, image=make_image(f"{i}.jpg")).save()
        self.assertEqual(self.entry.photos.count(), 3)

    def test_fourth_photo_raises_validation_error(self):
        for i in range(3):
            Photo(entry=self.entry, image=make_image(f"{i}.jpg")).save()
        with self.assertRaises(ValidationError):
            Photo(entry=self.entry, image=make_image("4th.jpg")).save()

    def test_updating_existing_photo_does_not_trigger_count_check(self):
        photo = Photo(entry=self.entry, image=make_image())
        photo.save()
        # Simulate an update — pk is already set so clean() must skip the guard
        photo.image = make_image("updated.jpg")
        photo.save()  # should not raise

    def test_uploaded_at_is_set_automatically(self):
        photo = Photo(entry=self.entry, image=make_image())
        photo.save()
        self.assertIsNotNone(photo.uploaded_at)

    def test_deleting_entry_cascades_to_photos(self):
        Photo(entry=self.entry, image=make_image()).save()
        self.entry.delete()
        self.assertEqual(Photo.objects.count(), 0)

    def test_photos_related_name_accessible_from_entry(self):
        Photo(entry=self.entry, image=make_image()).save()
        self.assertEqual(self.entry.photos.count(), 1)


# ---------------------------------------------------------------------------
# Entry model
# ---------------------------------------------------------------------------


class EntryModelTests(TestCase):
    def setUp(self):
        self.user = create_user()

    def _make_entry(self, entry_type=Entry.Type.MILESTONE):
        return Entry.objects.create(
            owner=self.user,
            content=b"bytes",
            type=entry_type,
            date=datetime.today().date(),
        )

    def test_default_type_is_milestone(self):
        entry = Entry(owner=self.user, content=b"x", date=datetime.today().date())
        self.assertEqual(entry.type, Entry.Type.MILESTONE)

    def test_content_stored_as_binary(self):
        data = b"\x00\xff\xab"
        entry = Entry.objects.create(
            owner=self.user,
            content=data,
            type=Entry.Type.EVENT,
            date=datetime.today().date(),
        )
        entry.refresh_from_db()
        self.assertEqual(bytes(entry.content), data)

    def test_deleting_user_cascades_to_entries(self):
        self._make_entry()
        self.user.delete()
        self.assertEqual(Entry.objects.count(), 0)

    def test_all_type_choices_are_valid(self):
        for choice in (Entry.Type.MILESTONE, Entry.Type.LESSON, Entry.Type.EVENT):
            entry = self._make_entry(entry_type=choice)
            self.assertEqual(entry.type, choice)


# ---------------------------------------------------------------------------
# Security — cross-user isolation
# ---------------------------------------------------------------------------


class CrossUserSecurityTests(TestCase):
    def setUp(self):
        self.user_a = create_user("a@test.com")
        self.user_b = create_user("b@test.com")

    def test_user_b_entries_not_visible_in_user_a_queryset(self):
        self.client.force_login(self.user_a)
        create_entry(self.client)
        self.client.force_login(self.user_b)
        create_entry(self.client)

        self.assertEqual(Entry.objects.filter(owner=self.user_a).count(), 1)
        self.assertEqual(Entry.objects.filter(owner=self.user_b).count(), 1)

    def test_entry_created_by_user_a_not_owned_by_user_b(self):
        self.client.force_login(self.user_a)
        create_entry(self.client)
        entry = Entry.objects.get(owner=self.user_a)
        self.assertNotEqual(entry.owner, self.user_b)


# ---------------------------------------------------------------------------
# Sticker model
# ---------------------------------------------------------------------------


class StickerModelTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(
            name="Test Pack",
            description="A test pack",
            artist="Test Artist",
        )

    def test_sticker_creation(self):
        sticker = Sticker.objects.create(pack=self.pack, name="Smile")
        self.assertIsNotNone(sticker.pk)
        self.assertEqual(sticker.name, "Smile")
        self.assertEqual(sticker.pack, self.pack)

    def test_sticker_str(self):
        sticker = Sticker.objects.create(pack=self.pack, name="Smile")
        self.assertEqual(str(sticker), "Smile")

    def test_sticker_pack_related_name(self):
        Sticker.objects.create(pack=self.pack, name="A")
        Sticker.objects.create(pack=self.pack, name="B")
        self.assertEqual(self.pack.stickers.count(), 2)

    def test_deleting_pack_cascades_to_stickers(self):
        sticker = Sticker.objects.create(pack=self.pack, name="Bye")
        self.pack.delete()
        self.assertEqual(Sticker.objects.filter(pk=sticker.pk).count(), 0)


# ---------------------------------------------------------------------------
# StickerPack model
# ---------------------------------------------------------------------------


class StickerPackModelTests(TestCase):
    def test_sticker_pack_creation(self):
        pack = StickerPack.objects.create(
            name="Fun Pack",
            description="Fun stickers",
            artist="Cool Artist",
        )
        self.assertIsNotNone(pack.pk)
        self.assertEqual(pack.name, "Fun Pack")


# ---------------------------------------------------------------------------
# OwnedPack model
# ---------------------------------------------------------------------------


class OwnedPackModelTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(
            name="My Pack",
            description="desc",
            artist="artist",
        )

    def test_owned_pack_creation(self):
        owned = OwnedPack.objects.create(owner=self.user, pack=self.pack)
        self.assertIsNotNone(owned.pk)
        self.assertEqual(owned.owner, self.user)
        self.assertEqual(owned.pack, self.pack)

    def test_purchase_date_set_automatically(self):
        owned = OwnedPack.objects.create(owner=self.user, pack=self.pack)
        self.assertIsNotNone(owned.purchase_date)

    def test_deleting_user_cascades_to_owned_packs(self):
        OwnedPack.objects.create(owner=self.user, pack=self.pack)
        self.user.delete()
        self.assertEqual(OwnedPack.objects.count(), 0)

    def test_deleting_pack_cascades_to_owned_packs(self):
        OwnedPack.objects.create(owner=self.user, pack=self.pack)
        self.pack.delete()
        self.assertEqual(OwnedPack.objects.count(), 0)


# ---------------------------------------------------------------------------
# StickerPosition model
# ---------------------------------------------------------------------------


class StickerPositionModelTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(name="Pack", description="d", artist="a")
        self.sticker = Sticker.objects.create(pack=self.pack, name="Star")
        self.entry = Entry.objects.create(
            owner=self.user,
            content=b"enc",
            type=Entry.Type.MILESTONE,
            date=datetime.today().date(),
        )

    def test_sticker_position_creation(self):
        pos = StickerPosition.objects.create(
            owner=self.user,
            sticker=self.sticker,
            page="page-1",
            x=10.5,
            y=20.5,
            width=50,
            height=50,
        )
        self.assertIsNotNone(pos.pk)
        self.assertEqual(pos.owner, self.user)
        self.assertEqual(pos.sticker, self.sticker)

    def test_deleting_owner_cascades_to_positions(self):
        StickerPosition.objects.create(
            owner=self.user,
            sticker=self.sticker,
            page="page-1",
            x=0,
            y=0,
            width=10,
            height=10,
        )
        self.user.delete()
        self.assertEqual(StickerPosition.objects.count(), 0)

    def test_deleting_sticker_cascades_to_positions(self):
        StickerPosition.objects.create(
            owner=self.user,
            sticker=self.sticker,
            page="page-1",
            x=0,
            y=0,
            width=10,
            height=10,
        )
        self.sticker.delete()
        self.assertEqual(StickerPosition.objects.count(), 0)


# ---------------------------------------------------------------------------
# serve_sticker view
# ---------------------------------------------------------------------------


class ServeStickerViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(name="Pack", description="d", artist="a")
        self.sticker = Sticker.objects.create(
            pack=self.pack,
            name="Star",
            image=make_image("sticker.png", fmt="PNG"),
        )

    def test_serve_existing_sticker_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("journal:serve-sticker", args=[self.sticker.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_serve_missing_sticker_returns_404(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("journal:serve-sticker", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(
            reverse("journal:serve-sticker", args=[self.sticker.pk])
        )
        self.assertIn(response.status_code, [301, 302])
        self.assertIn("/auth/login", response["Location"])


# ---------------------------------------------------------------------------
# sticker_panel view
# ---------------------------------------------------------------------------


class StickerPanelViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(name="Pack", description="d", artist="a")
        self.owned = OwnedPack.objects.create(owner=self.user, pack=self.pack)
        self.sticker = Sticker.objects.create(pack=self.pack, name="Star")

    def test_ajax_request_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("journal:sticker_panel"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)

    def test_non_ajax_request_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("journal:sticker_panel"))
        self.assertEqual(response.status_code, 400)

    def test_anonymous_user_redirects_to_login(self):
        response = self.client.get(
            reverse("journal:sticker_panel"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertIn(response.status_code, [301, 302])
        self.assertIn("/auth/login", response["Location"])

    def test_panel_contains_sticker_url(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("journal:sticker_panel"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertIn("packs", response.context)
        packs = response.context["packs"]
        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0]["pack"], self.pack)
        sticker_urls = [s["url"] for s in packs[0]["stickers"]]
        self.assertIn(
            reverse("journal:serve-sticker", args=[self.sticker.pk]),
            sticker_urls,
        )

    def test_user_only_sees_owned_packs(self):
        other_user = create_user("other@test.com")
        other_pack = StickerPack.objects.create(
            name="Other", description="d", artist="a"
        )
        OwnedPack.objects.create(owner=other_user, pack=other_pack)

        self.client.force_login(self.user)
        response = self.client.get(
            reverse("journal:sticker_panel"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        packs = response.context["packs"]
        pack_names = [p["pack"].name for p in packs]
        self.assertIn(self.pack.name, pack_names)
        self.assertNotIn(other_pack.name, pack_names)


# ---------------------------------------------------------------------------
# place_sticker view
# ---------------------------------------------------------------------------


class PlaceStickerViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(name="Pack", description="d", artist="a")
        self.sticker = Sticker.objects.create(pack=self.pack, name="Star")

    def test_anonymous_post_redirects_to_login(self):
        response = self.client.post(reverse("journal:place_sticker"))
        self.assertIn(response.status_code, [301, 302])
        self.assertIn("/auth/login", response["Location"])

    def test_non_post_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("journal:place_sticker"))
        self.assertEqual(response.status_code, 400)

    def test_valid_post_creates_position(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("journal:place_sticker"),
            data={
                "x": "10.5",
                "y": "20.5",
                "width": "50",
                "height": "50",
                "sticker_id": str(self.sticker.pk),
                "page_id": "page-1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StickerPosition.objects.count(), 1)
        pos = StickerPosition.objects.first()
        self.assertEqual(pos.owner, self.user)
        self.assertEqual(pos.sticker, self.sticker)
        self.assertEqual(pos.page, "page-1")

    def test_response_contains_placement_id(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("journal:place_sticker"),
            data={
                "x": "1",
                "y": "2",
                "width": "10",
                "height": "10",
                "sticker_id": str(self.sticker.pk),
                "page_id": "page-1",
            },
        )
        self.assertEqual(response.status_code, 200)
        placement_id = int(response.content.decode())
        self.assertEqual(placement_id, StickerPosition.objects.first().pk)

    def test_values_are_rounded_to_two_decimals(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("journal:place_sticker"),
            data={
                "x": "10.556",
                "y": "20.999",
                "width": "50.01",
                "height": "50.09",
                "sticker_id": str(self.sticker.pk),
                "page_id": "page-1",
            },
        )
        pos = StickerPosition.objects.first()
        self.assertEqual(float(pos.x), 10.56)
        self.assertEqual(float(pos.y), 21.0)
        self.assertEqual(float(pos.width), 50.01)
        self.assertEqual(float(pos.height), 50.09)


# ---------------------------------------------------------------------------
# delete_sticker_placement view
# ---------------------------------------------------------------------------


class DeleteStickerPlacementViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(name="Pack", description="d", artist="a")
        self.sticker = Sticker.objects.create(pack=self.pack, name="Star")
        self.position = StickerPosition.objects.create(
            owner=self.user,
            sticker=self.sticker,
            page="page-1",
            x=0,
            y=0,
            width=10,
            height=10,
        )

    def test_anonymous_delete_redirects_to_login(self):
        response = self.client.delete(
            reverse("journal:delete_sticker", args=[self.position.pk])
        )
        self.assertIn(response.status_code, [301, 302])
        self.assertIn("/auth/login", response["Location"])

    def test_non_delete_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("journal:delete_sticker", args=[self.position.pk])
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_own_placement_returns_200(self):
        self.client.force_login(self.user)
        response = self.client.delete(
            reverse("journal:delete_sticker", args=[self.position.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StickerPosition.objects.count(), 0)

    def test_delete_other_users_placement_is_safe(self):
        other = create_user("other@test.com")
        other_position = StickerPosition.objects.create(
            owner=other,
            sticker=self.sticker,
            page="page-1",
            x=0,
            y=0,
            width=10,
            height=10,
        )
        self.client.force_login(self.user)
        response = self.client.delete(
            reverse("journal:delete_sticker", args=[other_position.pk])
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            StickerPosition.objects.filter(pk=other_position.pk).count(), 1
        )

    def test_delete_nonexistent_placement_returns_500(self):
        self.client.force_login(self.user)
        response = self.client.delete(reverse("journal:delete_sticker", args=[99999]))
        self.assertEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# move_sticker_placement view
# ---------------------------------------------------------------------------


class MoveStickerPlacementViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(name="Pack", description="d", artist="a")
        self.sticker = Sticker.objects.create(pack=self.pack, name="Star")
        self.position = StickerPosition.objects.create(
            owner=self.user,
            sticker=self.sticker,
            page="page-1",
            x=10,
            y=20,
            width=50,
            height=50,
        )

    def test_anonymous_put_redirects_to_login(self):
        response = self.client.put(
            reverse("journal:move_sticker", args=[self.position.pk])
        )
        self.assertIn(response.status_code, [301, 302])
        self.assertIn("/auth/login", response["Location"])

    def test_non_put_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("journal:move_sticker", args=[self.position.pk])
        )
        self.assertEqual(response.status_code, 400)

    def test_move_own_placement_updates_position(self):
        self.client.force_login(self.user)
        response = self.client.put(
            reverse("journal:move_sticker", args=[self.position.pk]),
            data=json.dumps({"x": 99.5, "y": 88.5, "page": "page-2"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.position.refresh_from_db()
        self.assertEqual(float(self.position.x), 99.5)
        self.assertEqual(float(self.position.y), 88.5)
        self.assertEqual(self.position.page, "page-2")

    def test_move_other_users_placement_is_safe(self):
        other = create_user("other@test.com")
        other_position = StickerPosition.objects.create(
            owner=other,
            sticker=self.sticker,
            page="page-1",
            x=10,
            y=20,
            width=50,
            height=50,
        )
        self.client.force_login(self.user)
        response = self.client.put(
            reverse("journal:move_sticker", args=[other_position.pk]),
            data=json.dumps({"x": 0, "y": 0, "page": "page-1"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        other_position.refresh_from_db()
        self.assertEqual(float(other_position.x), 10)
        self.assertEqual(float(other_position.y), 20)

    def test_move_nonexistent_placement_returns_500(self):
        self.client.force_login(self.user)
        response = self.client.put(
            reverse("journal:move_sticker", args=[99999]),
            data=json.dumps({"x": 0, "y": 0, "page": "page-1"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# resize_sticker_placement view
# ---------------------------------------------------------------------------


class ResizeStickerPlacementViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(name="Pack", description="d", artist="a")
        self.sticker = Sticker.objects.create(pack=self.pack, name="Star")
        self.position = StickerPosition.objects.create(
            owner=self.user,
            sticker=self.sticker,
            page="page-1",
            x=0,
            y=0,
            width=50,
            height=50,
        )

    def test_anonymous_put_redirects_to_login(self):
        response = self.client.put(
            reverse("journal:resize_sticker", args=[self.position.pk])
        )
        self.assertIn(response.status_code, [301, 302])
        self.assertIn("/auth/login", response["Location"])

    def test_non_put_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("journal:resize_sticker", args=[self.position.pk])
        )
        self.assertEqual(response.status_code, 400)

    def test_resize_own_placement_updates_size(self):
        self.client.force_login(self.user)
        response = self.client.put(
            reverse("journal:resize_sticker", args=[self.position.pk]),
            data=json.dumps({"width": 200.5, "height": 150.25}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.position.refresh_from_db()
        self.assertEqual(float(self.position.width), 200.5)
        self.assertEqual(float(self.position.height), 150.25)

    def test_resize_other_users_placement_is_safe(self):
        other = create_user("other@test.com")
        other_position = StickerPosition.objects.create(
            owner=other,
            sticker=self.sticker,
            page="page-1",
            x=0,
            y=0,
            width=50,
            height=50,
        )
        self.client.force_login(self.user)
        response = self.client.put(
            reverse("journal:resize_sticker", args=[other_position.pk]),
            data=json.dumps({"width": 999, "height": 999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        other_position.refresh_from_db()
        self.assertEqual(float(other_position.width), 50)
        self.assertEqual(float(other_position.height), 50)

    def test_resize_nonexistent_placement_returns_500(self):
        self.client.force_login(self.user)
        response = self.client.put(
            reverse("journal:resize_sticker", args=[99999]),
            data=json.dumps({"width": 100, "height": 100}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# sticker_positions_for_page view
# ---------------------------------------------------------------------------


class StickerPositionsForPageViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.pack = StickerPack.objects.create(name="Pack", description="d", artist="a")
        self.sticker = Sticker.objects.create(pack=self.pack, name="Star")
        self.position = StickerPosition.objects.create(
            owner=self.user,
            sticker=self.sticker,
            page="page-1",
            x=10,
            y=20,
            width=50,
            height=50,
        )

    def test_anonymous_get_redirects_to_login(self):
        response = self.client.get(
            reverse("journal:sticker-positions", args=["page-1"])
        )
        self.assertIn(response.status_code, [301, 302])
        self.assertIn("/auth/login", response["Location"])

    def test_non_get_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("journal:sticker-positions", args=["page-1"])
        )
        self.assertEqual(response.status_code, 400)

    def test_get_returns_positions_for_page(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("journal:sticker-positions", args=["page-1"])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["stickers"]), 1)
        sticker_data = data["stickers"][0]
        self.assertEqual(sticker_data["id"], self.position.pk)
        self.assertEqual(float(sticker_data["x"]), 10)
        self.assertEqual(float(sticker_data["y"]), 20)
        self.assertEqual(float(sticker_data["width"]), 50)
        self.assertEqual(float(sticker_data["height"]), 50)
        self.assertIn("image_url", sticker_data)

    def test_get_returns_empty_for_other_page(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("journal:sticker-positions", args=["page-2"])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["stickers"]), 0)

    def test_user_only_sees_own_positions(self):
        other = create_user("other@test.com")
        other_sticker = Sticker.objects.create(pack=self.pack, name="Heart")
        StickerPosition.objects.create(
            owner=other,
            sticker=other_sticker,
            page="page-1",
            x=0,
            y=0,
            width=10,
            height=10,
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("journal:sticker-positions", args=["page-1"])
        )
        data = json.loads(response.content)
        self.assertEqual(len(data["stickers"]), 1)
        self.assertEqual(data["stickers"][0]["id"], self.position.pk)
