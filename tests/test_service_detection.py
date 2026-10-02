from app.domain_extraction import build_payload

def test_detects_services_from_row():
    result=build_payload('ASUNTO: crear usuarios', [(1,[['APELLIDOS Y NOMBRES','DNI','USUARIO'],['PEREZ, ANA','12345678','DOMINIO, SGD']])])
    assert result['usuarios'][0]['servicios_a_crear']==['dominio','sgd']

def test_detects_services_from_subject():
    result=build_payload('ASUNTO: solicitud de usuario SGD y DOMINIO', [(1,[['APELLIDOS Y NOMBRES','DNI'],['PEREZ, ANA','12345678']])])
    assert result['usuarios'][0]['servicios_a_crear']==['dominio','sgd']

def test_sgd_only_does_not_require_ad_group():
    result=build_payload('ASUNTO: SGD', [(1,[['APELLIDOS Y NOMBRES','DNI','USUARIO'],['PEREZ, ANA','12345678','SGD (ACCESO TOTAL), SIGA']])])
    user=result['usuarios'][0]
    assert user['servicios_a_crear']==['sgd']
    assert 'Falta configurar el grupo AD correspondiente al área.' not in user['observaciones']

def test_domain_only_does_not_add_sgd():
    result=build_payload('ASUNTO: dominio', [(1,[['APELLIDOS Y NOMBRES','DNI','USUARIO'],['PEREZ, ANA','12345678','DOMINIO']])])
    assert result['usuarios'][0]['servicios_a_crear']==['dominio']
