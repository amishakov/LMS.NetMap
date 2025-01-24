
from sqlmodel import Field, Relationship
from typing import Optional
from .import Base, IDDependent

class DNS_NS(IDDependent, Base, table=True):
    __tablename__ = "dns_ns"
    __table_args__ = {
        "comment": "Таблица предназначена для хранения DNS NS записей домена"
    }
    target_ip_id: str       = Field(foreign_key="ip.id", sa_column_kwargs={"comment":"Идентификатор IP адреса"})
    target_domain_id: str   = Field(foreign_key="domain.id", sa_column_kwargs={"comment":"Идентификатор домена"})
    value_domain_id: str    = Field(foreign_key="domain.id",sa_column_kwargs={"comment":"Идентификатор домена"})

    target_ip: Optional["IP"]           = Relationship(back_populates="dns_ns_target")
    target_domain: Optional["Domain"]   = Relationship(back_populates="dns_ns_target", sa_relationship_kwargs={"foreign_keys": "[DNS_NS.target_domain_id]"})
    value_domain: Optional["Domain"]    = Relationship(back_populates="dns_ns_value", sa_relationship_kwargs={"foreign_keys": "[DNS_NS.value_domain_id]"})