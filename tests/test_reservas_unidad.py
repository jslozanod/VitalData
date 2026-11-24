import pytest

from vitaldata.api import reservas


@pytest.mark.parametrize("c,esperado", [("Persona@Correo.com", "persona@correo.com"), ("300 123 4567", "3001234567"), ("+57 (300) 123-4567", "573001234567")])
def test_contacto_valido(c, esperado):
    assert reservas._validar_contacto(c) == esperado


@pytest.mark.parametrize("c", ["hola", "123", "a@b", "12345678901234567890", ""])
def test_contacto_invalido(c):
    with pytest.raises(reservas.Invalido):
        reservas._validar_contacto(c)


def test_codigo_de_cita_usa_alfabeto_sin_confusiones():
    for _ in range(200):
        c = reservas._codigo()
        assert c.startswith("VD-") and len(c) == 9 and not set("01OI") & set(c[3:])


@pytest.mark.parametrize("h,f", [("05:30", "madrugada"), ("07:00", "mañana"), ("11:30", "mañana"), ("12:00", "tarde"), ("17:30", "tarde"), ("18:00", "noche")])
def test_franja_del_dia(h, f):
    assert reservas.franja_del_dia(h) == f


def test_enmascarar_oculta_los_datos_personales():
    assert reservas._enmascarar("persona@correo.com") == "per***@correo.com"
    assert reservas._enmascarar("3001234567").endswith("567") and "300123" not in reservas._enmascarar("3001234567")


def test_agenda_de_30_minutos_de_7_a_18_30():
    assert reservas.HORAS[0] == "07:00" and reservas.HORAS[-1] == "18:30" and len(reservas.HORAS) == 24
