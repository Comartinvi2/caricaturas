"""/blog se reenvía a RankCoworker conservando la ruta y la query."""
from app import blog


def test_portada():
    assert blog.target("") == blog.ORIGIN
    assert blog.target("/") == blog.ORIGIN


def test_articulo_y_query():
    assert blog.target("mi-articulo-12/") == blog.ORIGIN + "/mi-articulo-12"
    assert blog.target("pagina/2", "a=1") == blog.ORIGIN + "/pagina/2?a=1"
