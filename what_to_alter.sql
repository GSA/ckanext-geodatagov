create index on harvest_object(guid);
create index on harvest_object(package_id);
create index on harvest_object_extra(harvest_object_id);
create index on package_extent(package_id);

create index on package_extra_revision(package_id);
create index on package_extra_revision(id);


--special
create index on revision(id);
drop index idx_package_resource_pkg_id_resource_id;

create index on resource(name);


create index on resource_group_revision(package_id);
create index on resource_group_revision(revision_id);
create index on resource_group_revision(id);

create index on resource_revision(id);
create index on resource_revision(resource_group_id);



drop INDEX idx_package_extra_current;
drop INDEX idx_package_extra_period;
drop INDEX idx_package_extra_period_package;
drop index idx_extra_id_pkg_id;

drop INDEX idx_package_tag_id ;

drop INDEX idx_package_tag_current ;
drop INDEX idx_package_tag_revision_pkg_id_tag_id ;
drop INDEX idx_period_package_tag ;

drop INDEX idx_resource_group_period ;
drop INDEX idx_resource_group_period_package ;
drop INDEX idx_resource_group_current ;

drop INDEX idx_resource_period;
drop INDEX idx_resource_current;
drop INDEX idx_resource_period_resource_group;


drop index idx_pkg_id;
drop index idx_pkg_name;
drop index idx_pkg_rev_id;
drop index idx_pkg_sid;
drop index idx_pkg_slname;
drop index idx_pkg_sname;
drop index idx_pkg_srev_id;
drop index idx_pkg_stitle;
drop index idx_pkg_suname;
drop index idx_pkg_title;
drop index idx_pkg_uname;
