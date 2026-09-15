from portgozu.snmp import SYS_NAME, _build_get, _decode_oid, _oid, _parse_response, _seq


def test_oid_roundtrip():
    raw = _oid(SYS_NAME)
    assert raw[0] == 0x06
    # strip tag+len
    length = raw[1]
    body = raw[2 : 2 + length]
    assert _decode_oid(body) == SYS_NAME


def test_build_get_is_sequence():
    pkt = _build_get(b"public", 7, [SYS_NAME])
    assert pkt[0] == 0x30
    assert b"public" in pkt


def test_parse_synthetic_response():
    # Minimal hand-built GetResponse with sysName = SW1
    from portgozu.snmp import _int, _len, _null, _octet

    oid = _oid(SYS_NAME)
    value = _octet(b"SW1")
    vb = _seq(oid + value)
    vblist = _seq(vb)
    pdu_body = _int(7) + _int(0) + _int(0) + vblist
    pdu = bytes([0xA2]) + _len(len(pdu_body)) + pdu_body
    msg = _seq(_int(1) + _octet(b"public") + pdu)
    bindings = _parse_response(msg)
    assert bindings[SYS_NAME] == "SW1"
