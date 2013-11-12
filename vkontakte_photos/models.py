# -*- coding: utf-8 -*-
from django.db import models
from vkontakte_api.utils import api_call
from vkontakte_api import fields
from vkontakte_api.models import VkontakteManager, VkontakteModel
from vkontakte_api.decorators import fetch_all
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

class AlbumRemoteManager(VkontakteManager):

    def fetch(self, user=None, group=None, ids=None, need_covers=False):
        if not user and not group:
            raise ValueError("You must specify user of group, which albums you want to fetch")
        if ids and not isinstance(ids, (tuple, list)):
            raise ValueError("Attribute 'ids' should be tuple or list")

        kwargs = {
            #need_covers
            #1 - будет возвращено дополнительное поле thumb_src. По умолчанию поле thumb_src не возвращается.
            'need_covers': int(need_covers)
        }
        #uid
        #ID пользователя, которому принадлежат альбомы. По умолчанию – ID текущего пользователя.
        if user:
            kwargs.update({'uid': user.remote_id})
        #gid
        #ID группы, которой принадлежат альбомы.
        if group:
            kwargs.update({'gid': group.remote_id})
        #aids
        #перечисленные через запятую ID альбомов.
        if ids:
            kwargs.update({'aids': ','.join(map(str, ids))})

        return super(AlbumRemoteManager, self).fetch(**kwargs)

class PhotoRemoteManager(VkontakteManager):

    def fetch(self, album, ids=None, limit=None, extended=False, offset=0, photo_sizes=False):
        if ids and not isinstance(ids, (tuple, list)):
            raise ValueError("Attribute 'ids' should be tuple or list")

        kwargs = {
            'aid': album.remote_id.split('_')[1],
            'extended': int(extended),
            'offset': int(offset),
            #photo_sizes
            #1 - позволяет получать все размеры фотографий.
            'photo_sizes': int(photo_sizes),
        }
        if album.owner:
            kwargs.update({'uid': album.owner.remote_id})
        elif album.group:
            kwargs.update({'gid': album.group.remote_id})
        if ids:
            kwargs.update({'pids': ','.join(map(str, ids))})
        if limit:
            kwargs.update({'limit': limit})

        # TODO: добавить поля
        #feed
        #Unixtime, который может быть получен методом newsfeed.get в поле date, для получения всех фотографий загруженных пользователем в определённый день либо на которых пользователь был отмечен. Также нужно указать параметр uid пользователя, с которым произошло событие.
        #feed_type
        #Тип новости получаемый в поле type метода newsfeed.get, для получения только загруженных пользователем фотографий, либо только фотографий, на которых он был отмечен. Может принимать значения photo, photo_tag.

        return super(PhotoRemoteManager, self).fetch(**kwargs)

class PhotosIDModel(VkontakteModel):
    class Meta:
        abstract = True

    methods_namespace = 'photos'

    remote_id = models.CharField(u'ID', max_length='20', help_text=u'Уникальный идентификатор', unique=True)

    @property
    def slug(self):
        return self.slug_prefix + str(self.remote_id)

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

        super(PhotosIDModel, self).parse(response)

        self.remote_id = self.get_remote_id(self.remote_id)

class Album(PhotosIDModel):
    class Meta:
        verbose_name = u'Альбом фотографий Вконтакте'
        verbose_name_plural = u'Альбомы фотографий Вконтакте'
        ordering = ['remote_id']

    remote_pk_field = 'aid'
    slug_prefix = 'album'

    # TODO: migrate to ContentType framework, remove vkontakte_users and vkontakte_groups dependencies
    owner = models.ForeignKey(User, verbose_name=u'Владелец альбома', null=True, related_name='photo_albums')
    group = models.ForeignKey(Group, verbose_name=u'Группа альбома', null=True, related_name='photo_albums')

    thumb_id = models.PositiveIntegerField()
    thumb_src = models.CharField(u'Обложка альбома', max_length='200')

    title = models.CharField(max_length='200')
    description = models.TextField()

    created = models.DateTimeField(db_index=True)
    updated = models.DateTimeField(null=True, db_index=True)

    size = models.PositiveIntegerField(u'Кол-во фотографий')
    privacy = models.PositiveIntegerField(u'Уровень доступа к альбому', null=True, choices=ALBUM_PRIVACY_CHOCIES)

    objects = models.Manager()
    remote = AlbumRemoteManager(remote_pk=('remote_id',), methods={
        'get': 'getAlbums',
#        'edit': 'editAlbum',
    })

    def __unicode__(self):
        return self.title

    def fetch_photos(self, *args, **kwargs):
        return Photo.remote.fetch(album=self, *args, **kwargs)

class Photo(PhotosIDModel):
    class Meta:
        verbose_name = u'Фотография Вконтакте'
        verbose_name_plural = u'Фотографии Вконтакте'
        ordering = ['remote_id']

    remote_pk_field = 'pid'
    slug_prefix = 'photo'
    likes_type = 'photo'

    album = models.ForeignKey(Album, verbose_name=u'Альбом', related_name='photos')

    owner = models.ForeignKey(User, verbose_name=u'Владелец фотографии', null=True, related_name='photos')
    group = models.ForeignKey(Group, verbose_name=u'Группа фотографии', null=True, related_name='photos')

    user = models.ForeignKey(User, verbose_name=u'Автор фотографии', null=True, related_name='photos_author')

    src = models.CharField(u'Иконка', max_length='200')
    src_big = models.CharField(u'Большая', max_length='200')
    src_small = models.CharField(u'Маленькая', max_length='200')
    src_xbig = models.CharField(u'Большая X', max_length='200')
    src_xxbig = models.CharField(u'Большая XX', max_length='200')

    width = models.PositiveIntegerField(null=True)
    height = models.PositiveIntegerField(null=True)

    likes = models.PositiveIntegerField(u'Лайков', default=0)
    comments = models.PositiveIntegerField(u'Комментариев', default=0)
    tags = models.PositiveIntegerField(u'Тегов', default=0)

    like_users = models.ManyToManyField(User, related_name='like_photos')

    text = models.TextField()

    created = models.DateTimeField(db_index=True)

    objects = models.Manager()
    remote = PhotoRemoteManager(remote_pk=('remote_id',), methods={
        'get': 'get',
    })

    def parse(self, response):
        super(Photo, self).parse(response)

        for field_name in ['likes','comments','tags']:
            if field_name in response and 'count' in response[field_name]:
                setattr(self, field_name, response[field_name]['count'])

        if 'user_id' in response:
            self.user = User.objects.get_or_create(remote_id=response['user_id'])[0]

        try:
            self.album = Album.objects.get(remote_id=self.get_remote_id(response['aid']))
        except Album.DoesNotExist:
            raise Exception('Impossible to save photo for unexisted album %s' % (self.get_remote_id(response['aid']),))

    def fetch_comments_parser(self):
        '''
        Fetch total ammount of comments
        TODO: implement fetching comments
        '''
        post_data = {
            'act':'photo_comments',
            'al': 1,
            'offset': 0,
            'photo': self.remote_id,
        }
        parser = VkontaktePhotosParser().request('/al_photos.php', data=post_data)

        self.comments = len(parser.content_bs.findAll('div', {'class': 'clear_fix pv_comment '}))
        self.save()

    def fetch_likes_parser(self):
        '''
        Fetch total ammount of likes
        TODO: implement fetching users who likes
        '''
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

    def update_and_get_likes(self, *args, **kwargs):
        self.likes = self.like_users.count()
        self.save()
        return self.like_users.all()

    @fetch_all(return_all=update_and_get_likes, default_count=1000)
    def fetch_likes(self, offset=0, *args, **kwargs):

        kwargs['offset'] = int(offset)
        kwargs['item_id'] = self.remote_id.split('_')[1]
        kwargs['owner_id'] = self.group.remote_id
        if isinstance(self.group, Group):
            kwargs['owner_id'] *= -1

        log.debug('Fetching likes of %s "%s" of owner "%s", offset %d' % (self._meta.module_name, self.remote_id, self.group, offset))

        ids = super(Photo, self).fetch_likes(*args, **kwargs)
        users = User.remote.fetch(ids=ids) if ids else []
        for user in users:
            self.like_users.add(user)

        return users

import signals