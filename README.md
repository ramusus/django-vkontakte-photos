# Django Vkontakte Photos

<a href="https://travis-ci.org/ramusus/django-vkontakte-photos" title="Django Vkontakte Photos Travis Status"><img src="https://secure.travis-ci.org/ramusus/django-vkontakte-photos.png"></a>

Приложение позволяет взаимодействовать с фотоальбомами и фотографиями Вконтакте используя стандартные модели Django через Вконтакте API

## Установка

    pip install django-vkontakte-photos

В `settings.py` необходимо добавить:

    INSTALLED_APPS = (
        ...
        'vkontakte_api',
        'vkontakte_photos',
    )

## Примеры использования

### Получение фотоальбомов группы через метод группы

Для этого необходимо установить дополнительно приложение
[`django-vkontakte-groups`](http://github.com/ramusus/django-vkontakte-groups/) и добавить его в `INSTALLED_APPS`

    >>> from vkontakte_groups.models import Group
    >>> group = Group.remote.fetch(ids=[16297716])[0]
    >>> group.fetch_albums()
    [<Album: Coca-Cola привозила кубок мира по футболу FIFA>,
     <Album: Старая реклама Coca-Cola>,
     '...(remaining elements truncated)...']

Фотоальбомы группы доступны через менеджер

    >>> group.photo_albums.count()
    47

Фотографии всех альбомов группы доступны через менеджер

    >>> group.photos.count()
    4432

### Получение фотоальбомов группы через менеджер

    >>> from vkontakte_groups.models import Group
    >>> from vkontakte_board.models import Album
    >>> group = Group.remote.fetch(ids=[16297716])[0]
    >>> Album.remote.fetch(group=group, ids=[106769855])
    [<Album: Coca-Cola привозила кубок мира по футболу FIFA>]

### Получение фотографий альбома пользователя через менеджер

Для этого необходимо установить дополнительно приложение
[`django-vkontakte-users`](http://github.com/ramusus/django-vkontakte-users/) и добавить его в `INSTALLED_APPS`

    >>> from vkontakte_users.models import User
    >>> from vkontakte_board.models import Album, Photo
    >>> user = User.remote.fetch(ids=[1])[0]
    >>> album = Album.remote.fetch(user=user, ids=[159337866])[0]
    >>> Photo.remote.fetch(album=album)
    [<Photo: Photo object>,
     <Photo: Photo object>,
     <Photo: Photo object>,
     <Photo: Photo object>]