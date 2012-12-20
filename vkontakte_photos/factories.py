from vkontakte_users.factories import UserFactory
from models import Album, Photo
from datetime import datetime
import factory
import random

class AlbumFactory(factory.Factory):
    FACTORY_FOR = Album

    remote_id = factory.Sequence(lambda n: '%s_%s' % (n, n))
    thumb_id = factory.Sequence(lambda n: n)

    created = datetime.now()
    updated = datetime.now()
    size = 1

class PhotoFactory(factory.Factory):
    FACTORY_FOR = Photo

    remote_id = factory.Sequence(lambda n: '%s_%s' % (n, n))
    user = factory.SubFactory(UserFactory)

    created = datetime.now()
    width = 10
    height = 10
