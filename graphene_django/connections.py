import graphene


class CountableConnection(graphene.relay.Connection):
    """
    Extended connection class with adds a totalCount field to the generated
    schema. The connection class is used by DjangoObjectType by default.
    """
    total_count = graphene.Int()

    class Meta:
        abstract = True

    def resolve_total_count(self, info):
        return self.iterable.count()
