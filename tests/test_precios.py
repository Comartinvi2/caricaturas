from app import config, fulfilment


def test_archivo_digital_a_9_90():
    assert config.PRICE_DIGITAL_CENTS == 990
    assert fulfilment.PRODUCTS["digital"]["cents"] == 990
