# -*- coding: utf-8 -*-
from django.db import models
from vkontakte_api.utils import api_call
from vkontakte_api import fields
from vkontakte_api.models import VkontakteManager, VkontakteModel
from vkontakte_users.models import User
from vkontakte_groups.models import Group
from parser import VkontaktePhotosParser
import logging
import re

log = logging.getLogger('vkontakte_photos')

ALBUM_PRIVACY_CHOCIES = (
    (0, u'Все пользователи'),
    (1, u'Только друзья'),
    (2, u'Друзья и друзья друзей'),
    (3, u'Только я')
)

class VkontakteAlbumsRemoteManager(VkontakteManager):

    def fetch(self, user=None, group=None, ids=None):
        if not user and not group:
            raise ValueError("You must specify user of group, which albums you want to fetch")
        if ids and not isinstance(ids, (tuple, list)):
            raise ValueError("Attribute 'ids' should be tuple or list")

        kwargs = {'need_covers': 1}
        if user:
            kwargs.update({'uid': user.remote_id})
        if group:
            kwargs.update({'gid': group.remote_id})
        if ids:
            kwargs.update({'aids': ','.join(ids)})
        return super(VkontakteAlbumsRemoteManager, self).fetch(**kwargs)

class VkontaktePhotosRemoteManager(VkontakteManager):

    def fetch(self, album, user=None, group=None, ids=None, limit=None, offset=None):
        if not user and not group:
            raise ValueError("You must specify user of group, which albums you want to fetch")
        if ids and not isinstance(ids, (tuple, list)):
            raise ValueError("Attribute 'ids' should be tuple or list")

        kwargs = {
            'aid': album.remote_id.split('_')[1],
            'extended': 1
        }
        if user:
            kwargs.update({'uid': user.remote_id})
        if group:
            kwargs.update({'gid': group.remote_id})
        if ids:
            kwargs.update({'pids': ','.join(ids)})
        if limit:
            kwargs.update({'limit': limit})
        if offset:
            kwargs.update({'offset': offset})
        return super(VkontaktePhotosRemoteManager, self).fetch(**kwargs)

class VkontaktePhotosIDModel(VkontakteModel):
    class Meta:
        abstract = True

    methods_namespace = 'photos'

    remote_id = models.CharField(u'ID', max_length='20', help_text=u'Уникальный идентификатор', unique=True)

    def get_remote_id(self, id):
        '''
        Returns unique remote_id, contains from 2 parts: remote_id of owner or group and remote_id of photo object
        '''
        if self.owner:
            remote_id = self.owner.remote_id
        elif self.group:
            remote_id = -1 * self.group.remote_id

        return '%s_%s' % (remote_id, id)

    def parse(self, response):

        owner_id = int(response.pop('owner_id'))
        if owner_id > 0:
            self.owner = User.objects.get_or_create(remote_id=owner_id)[0]
        else:
            self.group = Group.objects.get_or_create(remote_id=abs(owner_id))[0]

        super(VkontaktePhotosIDModel, self).parse(response)

        self.remote_id = self.get_remote_id(self.remote_id)

class Album(VkontaktePhotosIDModel):
    class Meta:
        db_table = 'vkontakte_photos_album'
        verbose_name = u'Альбом фотографий Вконтакте'
        verbose_name_plural = u'Альбомы фотографий Вконтакте'
        ordering = ['remote_id']

    remote_pk_field = 'aid'

    owner = models.ForeignKey(User, verbose_name=u'Владелец альбома', null=True, related_name='photo_albums')
    group = models.ForeignKey(Group, verbose_name=u'Группа альбома', null=True, related_name='photo_albums')

    thumb_id = models.PositiveIntegerField()
    thumb_src = models.CharField(u'Обложка альбома', max_length='200')

    title = models.CharField(max_length='200')
    description = models.TextField()

    created = models.DateTimeField()
    updated = models.DateTimeField(null=True)

    size = models.PositiveIntegerField(u'Кол-во фотографий')
    privacy = models.PositiveIntegerField(u'Уровень доступа к альбому', null=True, choices=ALBUM_PRIVACY_CHOCIES)

    objects = models.Manager()
    remote = VkontakteAlbumsRemoteManager(remote_pk=('remote_id',), methods={
        'get': 'getAlbums',
#        'edit': 'editAlbum',
    })

    @property
    def slug(self):
        return 'album%s' % self.remote_id

    def __unicode__(self):
        return self.title

    def fetch_photos(self):
        return Photo.remote.fetch(album=self, group=self.group, user=self.owner)

class Photo(VkontaktePhotosIDModel):
    class Meta:
        db_table = 'vkontakte_photos_photo'
        verbose_name = u'Фотография Вконтакте'
        verbose_name_plural = u'Фотографии Вконтакте'
        ordering = ['remote_id']

    remote_pk_field = 'pid'

    album = models.ForeignKey(Album, verbose_name=u'Альбом', related_name='photos')

    owner = models.ForeignKey(User, verbose_name=u'Владелец фотографии', null=True, related_name='photos')
    group = models.ForeignKey(Group, verbose_name=u'Группа фотографии', null=True, related_name='photos')

    user = models.ForeignKey(User, verbose_name=u'Автор фотографии', related_name='photos_author')

    src = models.CharField(u'Иконка', max_length='200')
    src_big = models.CharField(u'Большая', max_length='200')
    src_small = models.CharField(u'Маленькая', max_length='200')
    src_xbig = models.CharField(u'Большая X', max_length='200')
    src_xxbig = models.CharField(u'Большая XX', max_length='200')

    width = models.PositiveIntegerField(null=True)
    height = models.PositiveIntegerField(null=True)

    likes = models.PositiveIntegerField(u'Кол-во лайков', default=0)
    comments = models.PositiveIntegerField(u'Кол-во лайков', default=0)
    tags = models.PositiveIntegerField(u'Кол-во тегов', default=0)

    text = models.TextField()

    created = models.DateTimeField()

    objects = models.Manager()
    remote = VkontaktePhotosRemoteManager(remote_pk=('remote_id',), methods={
        'get': 'get',
    })

    @property
    def slug(self):
        return 'photo%s' % self.remote_id

    def parse(self, response):
        super(Photo, self).parse(response)

        for field_name in ['likes','comments','tags']:
            if field_name in response and 'count' in response[field_name]:
                setattr(self, field_name, response[field_name]['count'])

        self.user = User.objects.get_or_create(remote_id=response['user_id'])[0]
        try:
            self.album = Album.objects.get(remote_id=self.get_remote_id(response['aid']))
        except Album.DoesNotExist:
            raise Exception('Impossible to save photo for unexisted album %s' % (self.get_remote_id(response['aid']),))

    def fetch_comments(self):
        post_data = {
            'act':'photo_comments',
            'al': 1,
            'offset': 0,
            'photo': self.remote_id,
        }
        parser = VkontaktePhotosParser().request('/al_photos.php', data=post_data)

        self.comments = len(parser.content_bs.findAll('div', {'class': 'clear_fix pv_comment '}))
        self.save()

    def update_likes(self):
        post_data = {
            'act':'a_get_stats',
            'al': 1,
            'list': 'album%s' % self.album.remote_id,
            'object': 'photo%s' % self.remote_id,
        }
        parser = VkontaktePhotosParser().request('/like.php', data=post_data)

        values = re.findall(r'value="(\d+)"', parser.html)
        if len(values):
            self.likes = int(values[0])
            self.save()

import signals