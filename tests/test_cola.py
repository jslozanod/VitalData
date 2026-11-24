import math

import pytest

from vitaldata.models import cola


def test_erlang_c_un_servidor_es_la_utilizacion():
    # con c = 1, la probabilidad de esperar es rho = a
    assert cola.erlang_c(1, 0.5) == pytest.approx(0.5)


def test_erlang_c_valor_de_tablas():
    # valor clasico: c = 2, a = 1 -> C = 1/3
    assert cola.erlang_c(2, 1.0) == pytest.approx(1 / 3)


def test_erlang_c_satura():
    assert cola.erlang_c(3, 3.0) == 1.0 and cola.erlang_c(3, 5.0) == 1.0


def test_erlang_c_sin_carga():
    assert cola.erlang_c(4, 0.0) == 0.0


@pytest.mark.parametrize("c,a", [(0, 1.0), (-1, 1.0), (2, -0.1)])
def test_erlang_c_entradas_invalidas(c, a):
    with pytest.raises(ValueError):
        cola.erlang_c(c, a)


def test_espera_baja_al_aumentar_personal():
    esperas = [cola.espera_media_min(10, c, 30) for c in range(6, 12)]
    assert all(a > b for a, b in zip(esperas, esperas[1:]))


def test_espera_infinita_si_la_carga_supera_la_capacidad():
    assert math.isinf(cola.espera_media_min(10, 5, 30))      # 10/h x 0.5 h = 5 erlangs en 5 personas


def test_espera_cero_sin_llegadas():
    assert cola.espera_media_min(0, 3, 30) == 0.0


def test_personal_necesario_cumple_la_meta():
    for lam in (1, 3, 8, 15, 30):
        c = cola.personal_necesario(lam, 30, 15)
        assert cola.espera_media_min(lam, c, 30) <= 15


def test_personal_necesario_es_el_minimo():
    for lam in (3, 8, 15, 30):
        c = cola.personal_necesario(lam, 30, 15)
        if c > 1:
            assert cola.espera_media_min(lam, c - 1, 30) > 15


def test_personal_necesario_sin_llegadas_es_uno():
    assert cola.personal_necesario(0, 30, 15) == 1


def test_meta_negativa_es_error():
    with pytest.raises(ValueError):
        cola.personal_necesario(5, 30, -1)


def test_limite_superior_de_personal():
    assert cola.personal_necesario(500, 60, 0, c_max=20) == 20
