from djan.apps import AppConfig


class CrudappConfig(AppConfig):
    default_auto_field = 'djan.db.models.BigAutoField'
    name = 'crudapp'
