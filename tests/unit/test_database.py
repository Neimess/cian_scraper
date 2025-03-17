from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker

from db.models import Apartment, ApartmentImage, Base, User, UserConfig


@pytest.fixture(scope="session")
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine)
    session = testing_session_local()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


def test_create_user(test_db):
    test_db.rollback()  # Очистка возможных прошлых ошибок
    user = User(tg_id="12345", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    test_db.add(user)
    test_db.commit()

    saved_user = test_db.query(User).filter_by(tg_id="12345").first()
    assert saved_user is not None
    assert saved_user.tg_id == "12345"


def test_create_duplicate_user(test_db):
    test_db.rollback()
    user1 = User(tg_id="54321", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    user2 = User(tg_id="54321", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))

    test_db.add(user1)
    test_db.commit()

    test_db.add(user2)
    with pytest.raises(exc.IntegrityError):
        test_db.commit()
    test_db.rollback()  # Добавили очистку после ошибки


def test_create_duplicate_apartment_url(test_db):
    test_db.rollback()
    apartment1 = Apartment(title="Flat 1", url="https://example.com/apartment1")
    apartment2 = Apartment(title="Flat 2", url="https://example.com/apartment1")

    test_db.add(apartment1)
    test_db.commit()

    test_db.add(apartment2)
    with pytest.raises(exc.IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_create_userconfig_without_user(test_db):
    test_db.rollback()
    user_config = UserConfig(deal_type="sale", min_price=50000, max_price=200000)

    test_db.add(user_config)
    with pytest.raises(exc.IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_create_apartment(test_db):
    test_db.rollback()
    apartment = Apartment(title="Nice Apartment", price=50000, address="Main Street, 1", url="https://example.com/apartment2")
    test_db.add(apartment)
    test_db.commit()

    saved_apartment = test_db.query(Apartment).filter_by(title="Nice Apartment").first()
    assert saved_apartment is not None
    assert saved_apartment.price == 50000
    assert saved_apartment.address == "Main Street, 1"


def test_create_apartment_with_images(test_db):
    test_db.rollback()
    apartment = Apartment(title="Cozy Apartment", url="https://example.com/apartment3")
    image1 = ApartmentImage(url="https://example.com/image1.jpg", listing=apartment)
    image2 = ApartmentImage(url="https://example.com/image2.jpg", listing=apartment)

    test_db.add(apartment)
    test_db.add(image1)
    test_db.add(image2)
    test_db.commit()

    saved_apartment = test_db.query(Apartment).filter_by(title="Cozy Apartment").first()
    assert saved_apartment is not None
    assert len(saved_apartment.images) == 2


def test_update_apartment_price(test_db):
    test_db.rollback()
    apartment = Apartment(title="Luxury Flat", price=80000, url="https://example.com/apartment4")
    test_db.add(apartment)
    test_db.commit()

    apartment.price = 90000
    test_db.commit()

    updated_apartment = test_db.query(Apartment).filter_by(id=apartment.id).first()
    assert updated_apartment.price == 90000
