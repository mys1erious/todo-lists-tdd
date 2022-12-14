from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model

from ..models import Item, List


User = get_user_model()


class ItemModelTest(TestCase):
    def test_default_text(self):
        item = Item()
        self.assertEqual(item.text, '')

    def test_str_repr(self):
        item = Item(text='some text')
        self.assertEqual(str(item), 'some text')


class ListModelTest(TestCase):
    def test_get_absolute_url(self):
        lst = List.objects.create()
        self.assertEqual(lst.get_absolute_url(), f'/lists/{lst.id}/')

    def test_create_new_creates_list_and_first_item(self):
        List.create_new(first_item_text='new item text')
        new_item = Item.objects.first()
        self.assertEqual(new_item.text, 'new item text')
        new_list = List.objects.first()
        self.assertEqual(new_item.list, new_list)

    def test_create_new_optionally_saves_owner(self):
        user = User.objects.create()
        List.create_new(first_item_text='new item text', owner=user)
        new_list = List.objects.first()
        self.assertEqual(new_list.owner, user)

    def test_lists_can_have_owners(self):
        List(owner=User())  # shouldnt raise

    def test_list_owner_is_optional(self):
        List().full_clean() # shouldnt raise

    def test_create_returns_new_list_object(self):
        returned = List.create_new(first_item_text='new item text')
        new_list = List.objects.first()
        self.assertEqual(returned, new_list)

    def test_list_name_is_first_item_text(self):
        lst = List.objects.create()
        Item.objects.create(list=lst, text='first item')
        Item.objects.create(list=lst, text='second item')
        self.assertEqual(lst.name, 'first item')

    def test_share_with_add_adds_user_to_shared_with_query(self):
        user = User.objects.create(email='edith@example.com')
        lst = List.objects.create()
        lst.shared_with.add(user)

        self.assertIn(user, lst.shared_with.all())


class ListAndItemModelTest(TestCase):
    def test_item_is_related_to_list(self):
        lst = List.objects.create()
        item = Item()
        item.list = lst
        item.save()
        self.assertIn(item, lst.item_set.all())

    def test_list_ordering(self):
        list1 = List.objects.create()
        item1 = Item.objects.create(list=list1, text='i1')
        item2 = Item.objects.create(list=list1, text='item 2')
        item3 = Item.objects.create(list=list1, text='3')
        self.assertEqual(list(Item.objects.all()), [item1, item2, item3])

    def test_cant_save_empty_list_items(self):
        lst = List.objects.create()
        item = Item(list=lst, text='')
        with self.assertRaises(ValidationError):
            item.save()
            item.full_clean()

    def test_duplicate_items_are_invalid(self):
        lst = List.objects.create()
        Item.objects.create(list=lst, text='bla')
        with self.assertRaises(ValidationError):
            item = Item(list=lst, text='bla')
            item.full_clean()

    def test_CAN_save_same_item_to_diff_lists(self):
        list1 = List.objects.create()
        list2 = List.objects.create()
        Item.objects.create(list=list1, text='bla')
        item = Item(list=list2, text='bla')
        item.full_clean()  # shouldnt raise
