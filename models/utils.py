def recurse_set_attribute(obj, attributes, value):
    if len(attributes) == 1:
        obj[attributes[0]] = value
    else:
        recurse_set_attribute(
            obj[attributes[0]], attributes[1:], value
        )

def recurse_get_attribute(obj, attributes):
    if not isinstance(attributes, list):
        raise ValueError()

    if not attributes:
        return obj if obj else None

    return recurse_get_attribute(
        obj.get(attributes[0], {}), attributes[1:]
    )
