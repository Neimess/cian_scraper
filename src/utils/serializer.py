def to_dict(instance):
    return {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
        if getattr(instance, column.name) is not None and column.name not in ("id", "user_id")
    }
