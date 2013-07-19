# -*- coding: utf-8 -*-
from django.test import TestCase
from models import Album, Photo
from factories import AlbumFactory, PhotoFactory
from vkontakte_users.factories import UserFactory
from vkontakte_groups.factories import GroupFactory
from datetime import datetime
import simplejson as json

GROUP_ID = 16297716
ALBUM_ID = '-16297716_154228728'
PHOTO_ID = '-16297716_280118215'

class VkontaktePhotosTest(TestCase):

    def test_fetch_group_albums(self):

        group = GroupFactory(remote_id=GROUP_ID)

        self.assertEqual(Album.objects.count(), 0)

        albums = group.fetch_albums()

        self.assertTrue(len(albums) > 0)
        self.assertEqual(Album.objects.count(), len(albums))
        self.assertEqual(albums[0].group, group)

    def test_fetch_group_photos(self):

        group = GroupFactory(remote_id=GROUP_ID)
        album = AlbumFactory(remote_id=ALBUM_ID, group=group)

        self.assertEqual(Photo.objects.count(), 0)

        photos = album.fetch_photos(extended=True)

        self.assertTrue(len(photos) > 0)
        self.assertEqual(Photo.objects.count(), len(photos))
        self.assertEqual(photos[0].group, group)
        self.assertEqual(photos[0].album, album)
        self.assertTrue(photos[0].likes > 0)
        self.assertTrue(photos[0].comments > 0)

    def test_fetch_photo_likes(self):

        group = GroupFactory(remote_id=GROUP_ID)
        album = AlbumFactory(remote_id=ALBUM_ID, group=group)
        photo = PhotoFactory(remote_id=PHOTO_ID, album=album, group=group)

        self.assertEqual(photo.likes, 0)
        users = photo.fetch_likes(all=True)
        self.assertTrue(photo.likes > 0)
        self.assertEqual(photo.likes, len(users))

    def test_fetch_photo_likes_parser(self):

        group = GroupFactory(remote_id=GROUP_ID)
        album = AlbumFactory(remote_id=ALBUM_ID, group=group)
        photo = PhotoFactory(remote_id=PHOTO_ID, album=album)

        self.assertEqual(photo.likes, 0)
        photo.fetch_likes_parser()
        self.assertTrue(photo.likes > 0)

    def test_fetch_photo_comments_parser(self):

        group = GroupFactory(remote_id=GROUP_ID)
        album = AlbumFactory(remote_id=ALBUM_ID, group=group)
        photo = PhotoFactory(remote_id=PHOTO_ID, album=album)

        self.assertEqual(photo.comments, 0)
        photo.fetch_comments_parser()
        self.assertTrue(photo.comments > 0)

    def test_parse_album(self):

        response = '''{"response":[{"aid":"16178407","thumb_id":"96509883","owner_id":"6492","title":"qwerty",
            "description":"desc","created":"1298365200","updated":"1298365201","size":"3",
            "privacy":"3"},{"aid":"17071606","thumb_id":"98054577","owner_id":"-6492",
            "title":"","description":"","created":"1204576880","updated":"1229532461",
            "size":"3","privacy":"0"}]}
            '''
        instance = Album()
        owner = UserFactory(remote_id=6492)
        instance.parse(json.loads(response)['response'][0])
        instance.save()

        self.assertEqual(instance.remote_id, '6492_16178407')
        self.assertEqual(instance.thumb_id, 96509883)
        self.assertEqual(instance.owner, owner)
        self.assertEqual(instance.title, 'qwerty')
        self.assertEqual(instance.description, 'desc')
        self.assertEqual(instance.size, 3)
        self.assertEqual(instance.privacy, 3)
        self.assertIsNotNone(instance.created)
        self.assertIsNotNone(instance.updated)

        instance = Album()
        group = GroupFactory(remote_id=6492)
        instance.parse(json.loads(response)['response'][1])
        instance.save()

        self.assertEqual(instance.remote_id, '-6492_17071606')
        self.assertEqual(instance.group, group)

    def test_parse_photo(self):

        response = '''{"response":[{"pid":"146771291","aid":"100001227","owner_id":"6492",
            "src":"http://cs9231.vkontakte.ru/u06492/100001227/m_7875d2fb.jpg",
            "src_big":"http://cs9231.vkontakte.ru/u06492/100001227/x_cd563004.jpg",
            "src_small":"http://cs9231.vkontakte.ru/u06492/100001227/s_c3bba2a8.jpg",
            "src_xbig":"http://cs9231.vkontakte.ru/u06492/100001227/y_62a74569.jpg",
            "src_xxbig":"http://cs9231.vkontakte.ru/u06492/100001227/z_793e9682.jpg",
            "text":"test","user_id":6492,"width":10,"height":10,
            "created":"1298365200"},{"pid":"146772677","aid":"100001227","owner_id":-6492,
            "src":"http://cs9231.vkontakte.ru/u06492/100001227/m_fd092958.jpg",
            "src_big":"http://cs9231.vkontakte.ru/u06492/100001227/x_1f8ec9b8.jpg",
            "src_small":"http://cs9231.vkontakte.ru/u06492/100001227/s_603d27ab.jpg",
            "src_xbig":"http://cs9231.vkontakte.ru/u06492/100001227/y_6938f576.jpg",
            "src_xxbig":"http://cs9231.vkontakte.ru/u06492/100001227/z_6a27e9fd.jpg",
            "text":"test","user_id":6492,"width":10,"height":10,
            "created":"1260887080"}]}
            '''
        instance = Photo()
        owner = UserFactory(remote_id=6492)
        album = AlbumFactory(remote_id='6492_100001227')
        instance.parse(json.loads(response)['response'][0])
        instance.save()

        self.assertEqual(instance.remote_id, '6492_146771291')
        self.assertEqual(instance.album, album)
        self.assertEqual(instance.owner, owner)
        self.assertEqual(instance.src, 'http://cs9231.vkontakte.ru/u06492/100001227/m_7875d2fb.jpg')
        self.assertEqual(instance.text, 'test')
        self.assertEqual(instance.width, 10)
        self.assertEqual(instance.height, 10)
        self.assertIsNotNone(instance.created)

        instance = Photo()
        group = GroupFactory(remote_id=6492)
        album = AlbumFactory(remote_id='-6492_100001227')
        instance.parse(json.loads(response)['response'][1])
        instance.save()

        self.assertEqual(instance.remote_id, '-6492_146772677')
        self.assertEqual(instance.album, album)
        self.assertEqual(instance.group, group)