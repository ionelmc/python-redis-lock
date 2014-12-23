def test_django_works():
    from django.core.cache import cache
    with cache.lock('whateva'):
        pass
