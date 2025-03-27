def to_dict(instance, exclude: set[str] = None):
    exclude = exclude or {"id", "user_id"}
    return {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
        if getattr(instance, column.name) is not None and column.name not in exclude
    }
