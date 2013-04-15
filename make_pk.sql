drop table old_new_source_id_mapping;
drop table harvest_source_after_load;
drop table tmp_to_delete;


ALTER TABLE activity
	ADD CONSTRAINT activity_pkey PRIMARY KEY (id);

ALTER TABLE activity_detail
	ADD CONSTRAINT activity_detail_pkey PRIMARY KEY (id);

ALTER TABLE group_extra_revision
	ADD CONSTRAINT group_extra_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE group_revision
	ADD CONSTRAINT group_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE harvest_object_extra
	ADD CONSTRAINT harvest_object_extra_pkey PRIMARY KEY (id);

ALTER TABLE member_revision
	ADD CONSTRAINT member_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE package_extra
	ADD CONSTRAINT package_extra_pkey PRIMARY KEY (id);

ALTER TABLE package_extra_revision
	ADD CONSTRAINT package_extra_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE package_relationship_revision
	ADD CONSTRAINT package_relationship_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE package_revision
	ADD CONSTRAINT package_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE package_tag
	ADD CONSTRAINT package_tag_pkey PRIMARY KEY (id);

ALTER TABLE package_tag_revision
	ADD CONSTRAINT package_tag_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE resource_group_revision
	ADD CONSTRAINT resource_group_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE resource_revision
	ADD CONSTRAINT resource_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE revision
	ADD CONSTRAINT revision_pkey PRIMARY KEY (id);

ALTER TABLE system_info_revision
	ADD CONSTRAINT system_info_revision_pkey PRIMARY KEY (id, revision_id);

ALTER TABLE term_translation
	ADD CONSTRAINT term_translation_pkey PRIMARY KEY (term, term_translation);

ALTER TABLE tracking_raw
	ADD CONSTRAINT tracking_raw_pkey PRIMARY KEY (user_key, access_timestamp);

ALTER TABLE tracking_summary
	ADD CONSTRAINT tracking_summary_pkey PRIMARY KEY (url, tracking_type, package_id, tracking_date);

