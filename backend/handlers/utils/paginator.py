async def paginator(qs, page: int = 1, page_size: int = 10) -> list:
    """
    异步分页器（用于查询集）
    :param qs: QuerySet object
    :param page: 第n页
    :param page_size: 每页条数
    :return:
    """
    offset = (page - 1) * page_size
    limit = page_size
    return await qs.offset(offset).limit(limit)


def paginator_list(data_list: list, page: int = 1, page_size: int = 10) -> list:
    """
    同步分页器（用于列表）
    :param data_list:
    :param page:
    :param page_size:
    :return:
    """
    offset = (page - 1) * page_size
    limit = page_size
    return data_list[offset: offset + limit]
