from datetime import datetime
import random

import factory
from vkontakte_groups.factories import GroupFactory
from vkontakte_users.factories import UserFactory

from . import models


class AlbumFactory(factory.DjangoModelFactory):

    remote_id = factory.LazyAttributeSequence(lambda o, n: '-%s_%s' % (o.group.remote_id, n))
    thumb_id = factory.Sequence(lambda n: n)

    group = factory.SubFactory(GroupFactory)

    created = factory.LazyAttribute(lambda o: datetime.now())
    updated = factory.LazyAttribute(lambda o: datetime.now())
    size = 1

    class Meta:
        model = models.Album


class PhotoFactory(factory.DjangoModelFactory):

    remote_id = factory.LazyAttributeSequence(lambda o, n: '%s_%s' % (o.group.remote_id, n))
    user = factory.SubFactory(UserFactory)
    album = factory.SubFactory(AlbumFactory)
    group = factory.SubFactory(GroupFactory)

    created = factory.LazyAttribute(lambda o: datetime.now())
    actions_count = factory.LazyAttribute(lambda o: random.randrange(100))
    width = 10
    height = 10

    class Meta:
        model = models.Photo
