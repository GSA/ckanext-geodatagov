"""
Mixin for Flask-specific functionality. This aides the migration between Pylons and Flask.
"""
import ckan.plugins as p

import ckanext.geodatagov.cli as cli


class MixinPlugin(p.SingletonPlugin):

    # IClick
    p.implements(p.IClick)

    def get_commands(self) -> list:
        return cli.get_commands()

    # IConfigurer
    def update_config(self, config):
        # TODO remove template/templates_2_8 and move templates/templates_new
        # to templates once we're off of CKAN 2.8.
        #
        # Using a separate dir for templates avoids having to maintain
        # backwards compatibility using a sprinkling of conditionals. We don't
        # anticipate adding new features to the existing 2.8 templates.
        p.toolkit.add_template_directory(config, "../templates/templates_new")
        p.toolkit.add_resource("../fanstatic_library", "geodatagov")
