import datetime

from unittest.mock import patch, Mock

import pytest


@pytest.fixture
def reactive_snap():
    import_patch = patch.dict(
        "sys.modules", {"charms": Mock(),
                        "charms.layer": Mock(),
                        "charms.reactive.helpers": Mock()})
    with import_patch:
        import reactive.snap
        return reactive.snap


def test_fails_with_no_store_assertions(reactive_snap):
    bundle = """\
type: model
authority-id: generic
series: 16
brand-id: generic
model: generic-classic
classic: true
timestamp: 2017-07-27T00:00:00.0Z
sign-key-sha3-384: d-JcZF9nD9eBw7bwMnH61x-bklnQOhQud1Is6o_cn2wTj8EYDi9musrIT9z2MdAa

AcLBXAQAAQoABgUCWYuXiAAKCRAdLQyY+/mCiST0D/0XGQauzV2bbTEy6DkrR1jlNbI6x8vfIdS8
KvEWYvzOWNhNlVSfwNOkFjs3uMHgCO6/fCg03wGXTyV9D7ZgrMeUzWrYp6EmXk8/LQSaBnff86XO
4/vYyfyvEYavhF0kQ6QGg8Cqr0EaMyw0x9/zWEO/Ll9fH/8nv9qcQq8N4AbebNvNxtGsCmJuXpSe
2rxl3Dw8XarYBmqgcBQhXxRNpa6/AgaTNBpPOTqgNA8ZtmbZwYLuaFjpZP410aJSs+evSKepy/ce
+zTA7RB3384YQVeZDdTudX2fGtuCnBZBAJ+NYlk0t8VFXxyOhyMSXeylSpNSx4pCqmUZRyaf5SDS
g1XxJet4IP0stZH1SfPOwc9oE81/bJlKsb9QIQKQRewvtUCLfe9a6Vy/CYd2elvcWOmeANVrJK0m
nRaz6VBm09RJTuwUT6vNugXSOCeF7W3WN1RHJuex0zw+nP3eCehxFSr33YrVniaA7zGfjXvS8tKx
AINNQB4g2fpfet4na6lPPMYM41WHIHPCMTz/fJQ6dZBSEg6UUZ/GiQhGEfWPBteK7yd9pQ8qB3fj
ER4UvKnR7hcVI26e3NGNkXP5kp0SFCkV5NQs8rzXzokpB7p/V5Pnqp3Km6wu45cU6UiTZFhR2IMT
l+6AMtrS4gDGHktOhwfmOMWqmhvR/INF+TjaWbsB6g==
"""
    with pytest.raises(reactive_snap.InvalidBundleError):
        reactive_snap.parse_store_assertion(bundle)


def test_single_store_assertion_found(reactive_snap):
    bundle = """\
type: store
authority-id: canonical
store: jbRWNnfXpDi0G5GD7LEZqbpSqfWcUtFi
operator-id: eJ8VwwkInXdLo5nIgoSKH8j95qs6BQ7D
timestamp: 2017-11-24T12:10:19.881852Z
url: http://firestorm.local
sign-key-sha3-384: BWDEoaqyr25nF5SNCvEv2v7QnM9QsfCc0PBMYD_i2NGSQ32EF2d4D0hqUel3m8ul

AcLBUgQAAQoABgUCWhgMKwAA3gYQAK68FSpGO3MQTOHuXar15Te7nf7RKa/5gJR2jIDf45XSVhYt
fsWdX5yEaRwoXWor84Tesm1XtYodyNRbBAKmz7a/1/tT105UxtnflO1Y42Yb4AliFtvW7Sc1eHO3
pg/ZAhx/2LmchBFJURon+vWi/scCr6GkUoQ+xNvCQpA0hWPfD4BnS5TJjhiA8PyGQWTLmyms5jbK
5AhIdogFKpPfmeaSCgSjz2OsMMJYQO639A2gmoT2zSHqJs4+/bTb2Oq4j08Am7Wv28vyVglWdedc
QKZuBJ/sepmZzHcWHNb65z3+KT+VC12LLQd/I+SxUkTsBNKC1mwpY39PrAsJDMCltxCepKmti0T6
hwYCYrrA6vBXjqoSRyW/YzDKRBoVpN3GwCE/1DmuxNFN2CUn4SM+q+SYmCuIaoDCmMyk6P9jrHyv
JO8V/ctnZ0FvdrwnXFQDH6HY5rojjyEyjlZo6M8H2SunLX0u/goVh38D8o0bEmX/cZEKtTZx7ml+
lxDMSobdfIYPBl4FjVGHY+Zkdso0xQjctG1nNhkeYJQswLqfHEEdwaeCyGBh42cQfFLqxd0qK36M
M49U7JumoWH6aclbo0RXGKDI9vsBRnmOOaCUus9gbbrNUs6MTst+RCPXqXPi4tzbTtRAY5jd8LWv
9/ZUS/A2VSNUaiKvfdzG6cnzr70R
"""
    parsed = reactive_snap.parse_store_assertion(bundle)
    assert 'store' == parsed.pop('type')
    assert 'canonical' == parsed.pop('authority-id')
    assert 'jbRWNnfXpDi0G5GD7LEZqbpSqfWcUtFi' == parsed.pop('store')
    assert 'eJ8VwwkInXdLo5nIgoSKH8j95qs6BQ7D' == parsed.pop('operator-id')
    assert datetime.datetime(2017, 11, 24, 12, 10, 19, 881852) == \
        parsed.pop('timestamp')
    assert 'http://firestorm.local' == parsed.pop('url')
    assert 'BWDEoaqyr25nF5SNCvEv2v7QnM9QsfCc0PBMYD_i2NGSQ32EF2d4D0hqUel3m8ul'\
        == parsed.pop('sign-key-sha3-384')
    assert {} == parsed


def test_non_store_assertion_skipped(reactive_snap):
    bundle = """\
type: account-key
authority-id: canonical
revision: 3
public-key-sha3-384: nCEscCRi548D-Y_p4suNut-MKukEohPtlcLQDpOkhfNq4erMHpZW0Mi-UhBrWq7Y
account-id: canonical
name: staging-store
since: 2016-04-01T00:00:00.0Z
body-length: 717
sign-key-sha3-384: e2r8on4LgdxQSaW5T8mBD5oC2fSTktTVxOYa5w3kIP4_nNF6L7mt6fOJShdOGkKu

ACBBTQRWhcGAARAA2KEb0USZZ8eT5iJy+LvknYk9DA5vO6CdzEsCi2lQHaMGDbakzkWLNDH3q2lO
F1/FI4YBIOfsU+riPLQNK6RPwD0xQvAkzsJ9kOuSn5RBjEN5TfNLNmHfRtVGRW5sZmiXz+g5LSLq
fSoAjhcOeEbbjm+ZM2H3MKR5HrbMA5tcxKVe7n8qESK1CNQQtUCit8H9eW1UpKskX1BmYwhe7+02
tQByfFTFcgLdDeH0xnpfGZCx2Voe+6rQDNLUxdLr8E6DgPxV4rkhSKtiW21wCez0n+I3udbeZmG0
xkYuUqV0b824gajsf9N052NGqc//Hqh/4mcQseuYwCK9a5Rxsl6cHSes3jf/y3nNXk+eKpZjZ575
SQ/o3jG7TSpXmcfcqaUOH7bj1DAI2cGx/D9TcpNzx6iPrmNhQ0JZnTXKQgfOgFW+4gy2vXszKCZT
6NqHz4c07tarSFU+oKC/hdld7HJZSxgUMY7fayeezHt6dVDmHoxRDlZC1aNR8wcf/Itt96rzQZ1l
R+9lMoJbI2j3U08XMGQzc9SOH+S1QtrdBY6jxnqXK3EFFXlmbVAfH+dEbT5Okw7a+HT5E3r4HeFt
LrZtbv5zqWZgR9sdBDCxujluPbP7EJQvTe6XGqTeiPXA24OQiQ34iyop24sghDuIw/LbS/E3LVqM
vXGKzH5Xs1QEfUEAEQEAAQ==

AcLBXAQAAQoABgUCV86jcwAKCRAHKljtl9kuLuMFEAC//GdKg7EYQYfo+M/SOpBq8FXTEIeLQz1V
Oz7HdJKGgn5118cTN+Ll0l3n/bKIITKJ9iAxaJSpLni5Hq5e+a/HLjTHd2jAmCCgf+G3izLb4VZn
ALR0SRzqmRRawkEYyarxnVPhTslZr6r4fq+TE/4giRyngBBywnZlkTZbDTZz6GG0jf7kR5nZDUA9
Mh0D+FHn6iWPOwsRdccf7dpBUkiA25B/qOVDl+S/8XMkYYMkBw8JHs46+0u2F2xQ1YR79ToRDoIZ
rRkxM8LLb/TwIEkSgzb6sqVtbConLIuY1MYFdArkbMgAJJZKdSTijIhw8ltwTHBtSndtZsXBuhsC
5x2PnxFpExwHF7fCsX2QK/mcs5fc/BKeJcl80L7duQfwno2X94TkpxDI5Na+j1VK8XiIAugXtdxc
Nl12VBrZZVIcyJQ+tmIQNtGu++yB0SJe03cebysXlRfSlL2ed21UlV+Ep4Y6yp0dxH904ctTuthJ
jLTsAAZzL3pMPGhZwhWSfN+sgvtsjda+G+dB3PDBqL1rAw/JeNayFOjFVIKpiywqLJW8cBUY3CTV
pU22O7I5JrBxOsRzJ1YNXXSOS7qjjU+UMeMygPOeIqv7gLGpRrFA+ya/JqlpG+7HCdEjUCxylMWS
W4QebTCwUIhW7p/3A3jqFDbX5nW+/902WkPy9glm0A==

type: account
authority-id: canonical
account-id: bFi5nYN2Rp9NZk0lghmMq3qb93YxuyGJ
display-name: Adam Collard
timestamp: 2017-11-10T16:13:15.284308Z
username: sparkiegeeks
validation: unproven
sign-key-sha3-384: nCEscCRi548D-Y_p4suNut-MKukEohPtlcLQDpOkhfNq4erMHpZW0Mi-UhBrWq7Y

AcLBUgQAAQoABgUCWgXQGwAAF+IQALKT8nlA8PBIih9Go0wTKU5ZpSG7dF2kNlCazWnj84Jh8FnY
wRSuTM2MM0MRdCtAUDsUWY3xRxNQIxSVUvDCo2oqWl+iJBvbDCQdHxQ/bC0F98xSTR02GSuQLiBZ
4eU27MwpdkfTBakwP/ewYp0Zm1CxSgbpxSdNwkYakY6KLpqkWHTpKn+1s5mUEDdrEGLjdbJD2S1p
b59jrvk1X6lYJLCBrHaBMwLW6LIa2oXzuwoZZNwG2egIxc879saM02IONe9c63avF7JMuGawePjI
g2XLdZ4jMUAeo8L8ij0etFTjAYbHdmfsD665qXhboETMAXp3WedSDhvT1SfWMvKF8x44ersP7fi5
vMwA7lT5TeVGDcxnFrBi4sbasn9ntZ1c4oppTYVPSIh/q11r96S+U+6edljSmd8YBt/mFm6RQfSo
+tAAOs0IqsEBc2Tp5v9uLovlWovAiHqXuzvsLgM1CxzYhVY+WSRIF5QZn5maJasrtdhxCpZEWvo6
yAZH8jC/okTF/PSn/VXVyUXX6x0zBnRf+l8TFCUbgyOp9ByymKrXq2V5A3OWqzXpc3l3/jCarknN
3m8WeQVOeJmSeni2e/d5kUBN2qkuUBrEEGaV85NyMNReN6sbbPldKFmj0yQWu7lCs4UpfMuf2vTg
4yw0W4y5wGzzX5lYA/+6uvOdViO+

type: store
authority-id: canonical
store: nwEedlRiRTOKq9e7EU0cYuUb3klHntsX
operator-id: bFi5nYN2Rp9NZk0lghmMq3qb93YxuyGJ
timestamp: 2017-12-01T11:44:21.460942Z
url: http://snapstore-snap
sign-key-sha3-384: nCEscCRi548D-Y_p4suNut-MKukEohPtlcLQDpOkhfNq4erMHpZW0Mi-UhBrWq7Y

AcLBUgQAAQoABgUCWiFAlQAAHcYQAFTgDTYmNBO3Ce/D7Q2R65Ui9Y7IjazORUNTu/80IO6iRzyH
vi+CZc4GdiZpNENiu2VaMYNj/dHW6rh22YdB/Yk9HU8Jm+HFxeN5E5RsxrCkYpEQKNrylUBklK7B
wnWTnBxYFQTq5ZJfEG/GYHsBYrp/JBDxGIQ754U9HXmQroZPUF3nn7mgsHTRIhxp4i8qrjZHuiOq
9iaqtuhW1ugyJiDsmCDjG0mJJ97pn7pxBAjc/VpyQJ2pajmF2UXhaL9skRDTUzoRh/jZE1QedTZT
gAnVxiHsl+mJVSmNIISnI3g4TopjXp1ChpgJsUOAvHbJrca77IXBtow/KqEMUSuT+OZYjrWUHdTp
+STMbrWzXWtjXeZeBokKMSWB3e98O8EpH+YTccYW4RSUC78bIP9aQi7anLXV0o1gxit2NdCMzQGQ
fYOlhd+23bEQSMqQRIUC2LGMTy4VrqNBo5pPiWp6VJGMBrSgkn1JxVQNcdAr3JdqtTbLaP6d3vHu
e9JukQzPKIlZ1N11CzUNo+bff2QqinuSH+dcYxBLy888cWUl/Bd1UL5MjxD5GhxE/glxhQ6W5rqA
+J0d/A6vcSc4hi7LYzrTd//uHwzBqztkh5hZUzRoqwtRMtXWDqw7rV0zxsrllyZOY/5gJG8IfxXJ
X3FALLQu/ZQVACz9KGvXOYgmJRV4
"""
    parsed = reactive_snap.parse_store_assertion(bundle)
    assert 'store' == parsed.pop('type')
    assert 'canonical' == parsed.pop('authority-id')
    assert 'nwEedlRiRTOKq9e7EU0cYuUb3klHntsX' == parsed.pop('store')
    assert 'bFi5nYN2Rp9NZk0lghmMq3qb93YxuyGJ' == parsed.pop('operator-id')
    assert datetime.datetime(2017, 12, 1, 11, 44, 21, 460942) == \
        parsed.pop('timestamp')
    assert 'http://snapstore-snap' == parsed.pop('url')
    assert 'nCEscCRi548D-Y_p4suNut-MKukEohPtlcLQDpOkhfNq4erMHpZW0Mi-UhBrWq7Y'\
        == parsed.pop('sign-key-sha3-384')
    assert {} == parsed
