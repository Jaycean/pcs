import os
from textwrap import dedent
from unittest import mock, skipUnless, TestCase

from pcs.cli.booth import command as booth_cmd

from pcs_test.tools.assertions import AssertPcsMixin
from pcs_test.tools.misc import (
    get_test_resource as rc,
    get_tmp_dir,
    get_tmp_file,
    outdent,
    write_file_to_tmpfile,
)
from pcs_test.tools.pcs_runner import PcsRunner


EMPTY_CIB = rc("cib-empty.xml")

BOOTH_RESOURCE_AGENT_INSTALLED = os.path.exists(
    "/usr/lib/ocf/resource.d/pacemaker/booth-site"
)
need_booth_resource_agent = skipUnless(
    BOOTH_RESOURCE_AGENT_INSTALLED,
    "test requires resource agent ocf:pacemaker:booth-site"
    " which is not installed",
)


class BoothMixinNoFiles(AssertPcsMixin):
    def setUp(self):
        # pylint cannot possibly know this is being mixed into TestCase classes
        # pylint: disable=invalid-name
        self.pcs_runner = PcsRunner(None)


class BoothMixin(AssertPcsMixin):
    def setUp(self):
        # pylint cannot possibly know this is being mixed into TestCase classes
        # pylint: disable=invalid-name
        self.booth_dir = get_tmp_dir("tier1_booth")
        self.booth_cfg_path = os.path.join(self.booth_dir.name, "booth.cfg")
        self.booth_key_path = os.path.join(self.booth_dir.name, "booth.key")
        self.temp_cib = get_tmp_file("tier1_booth")
        write_file_to_tmpfile(EMPTY_CIB, self.temp_cib)
        self.pcs_runner = PcsRunner(self.temp_cib.name)

    def tearDown(self):
        # pylint cannot possibly know this is being mixed into TestCase classes
        # pylint: disable=invalid-name
        self.temp_cib.close()
        self.booth_dir.cleanup()

    def fake_file(self, command):
        return "{0} --booth-conf={1} --booth-key={2}".format(
            command, self.booth_cfg_path, self.booth_key_path,
        )

    def ensure_booth_config_exists(self):
        if not os.path.exists(self.booth_cfg_path):
            with open(self.booth_cfg_path, "w") as config_file:
                config_file.write("")

    def ensure_booth_config_not_exists(self):
        if os.path.exists(self.booth_cfg_path):
            os.remove(self.booth_cfg_path)
        if os.path.exists(self.booth_key_path):
            os.remove(self.booth_key_path)

    def assert_pcs_success(self, command, *args, **kwargs):
        # pylint: disable=signature-differs
        return super(BoothMixin, self).assert_pcs_success(
            self.fake_file(command), *args, **kwargs
        )

    def assert_pcs_fail(self, command, *args, **kwargs):
        # pylint: disable=signature-differs
        return super(BoothMixin, self).assert_pcs_fail(
            self.fake_file(command), *args, **kwargs
        )

    def assert_pcs_fail_original(self, *args, **kwargs):
        return super(BoothMixin, self).assert_pcs_fail(*args, **kwargs)


class SetupTest(BoothMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.pcs_runner.cib_file = None

    def test_success_setup_booth_config(self):
        self.ensure_booth_config_not_exists()
        self.assert_pcs_success(
            "booth setup sites 1.1.1.1 2.2.2.2 arbitrators 3.3.3.3"
        )
        with open(self.booth_cfg_path, "r") as config_file:
            self.assertEqual(
                dedent(
                    """\
                    authfile = {0}
                    site = 1.1.1.1
                    site = 2.2.2.2
                    arbitrator = 3.3.3.3
                    """.format(
                        self.booth_key_path
                    )
                ),
                config_file.read(),
            )
        with open(self.booth_key_path, "rb") as key_file:
            self.assertEqual(64, len(key_file.read()))

    def test_overwrite_existing_mocked_config(self):
        self.ensure_booth_config_exists()
        self.assert_pcs_success(
            "booth setup sites 1.1.1.1 2.2.2.2 arbitrators 3.3.3.3",
        )
        self.ensure_booth_config_not_exists()

    def test_fail_on_multiple_reasons(self):
        self.assert_pcs_fail(
            "booth setup sites 1.1.1.1 arbitrators 1.1.1.1 2.2.2.2 3.3.3.3",
            (
                "Error: lack of sites for booth configuration (need 2 at least)"
                ": sites '1.1.1.1'\n"
                "Error: odd number of peers is required (entered 4 peers)\n"
                "Error: duplicate address for booth configuration: '1.1.1.1'\n"
                "Error: Errors have occurred, therefore pcs is unable to "
                "continue\n"
            ),
        )

    def test_refuse_partialy_mocked_environment(self):
        self.assert_pcs_fail_original(
            "booth setup sites 1.1.1.1 2.2.2.2 arbitrators 3.3.3.3"
            " --booth-conf=/some/file",  # no --booth-key!
            (
                "Error: When --booth-conf is specified, --booth-key must be "
                "specified as well\n"
            ),
        )
        self.assert_pcs_fail_original(
            "booth setup sites 1.1.1.1 2.2.2.2 arbitrators 3.3.3.3"
            " --booth-key=/some/file",  # no --booth-conf!
            (
                "Error: When --booth-key is specified, --booth-conf must be "
                "specified as well\n"
            ),
        )

    def test_show_usage_when_no_site_specified(self):
        self.assert_pcs_fail(
            "booth setup arbitrators 3.3.3.3",
            stdout_start="\nUsage: pcs booth <command>\n    setup",
        )
        self.assert_pcs_fail(
            "booth setup",
            stdout_start="\nUsage: pcs booth <command>\n    setup",
        )


class DestroyTest(BoothMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.pcs_runner.cib_file = None

    def test_failed_when_using_mocked_booth_env(self):
        self.assert_pcs_fail(
            "booth destroy",
            (
                "Error: Specified options '--booth-conf', '--booth-key' are "
                "not supported in this command\n"
            ),
        )


class BoothTest(BoothMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.pcs_runner.cib_file = None
        self.ensure_booth_config_not_exists()
        self.assert_pcs_success(
            "booth setup sites 1.1.1.1 2.2.2.2 arbitrators 3.3.3.3"
        )


class AddTicketTest(BoothTest):
    def test_success_add_ticket(self):
        self.assert_pcs_success("booth ticket add TicketA expire=10")
        with open(self.booth_cfg_path, "r") as config_file:
            self.assertEqual(
                dedent(
                    """\
                    authfile = {0}
                    site = 1.1.1.1
                    site = 2.2.2.2
                    arbitrator = 3.3.3.3
                    ticket = "TicketA"
                      expire = 10
                    """.format(
                        self.booth_key_path
                    )
                ),
                config_file.read(),
            )

    def test_fail_on_bad_ticket_name(self):
        self.assert_pcs_fail(
            "booth ticket add @TicketA",
            (
                "Error: booth ticket name '@TicketA' is not valid, use "
                "alphanumeric chars or dash\n"
                "Error: Errors have occurred, therefore pcs is unable to "
                "continue\n"
            ),
        )

    def test_fail_on_duplicit_ticket_name(self):
        self.assert_pcs_success("booth ticket add TicketA")
        self.assert_pcs_fail(
            "booth ticket add TicketA",
            (
                "Error: booth ticket name 'TicketA' already exists in "
                "configuration\n"
                "Error: Errors have occurred, therefore pcs is unable to "
                "continue\n"
            ),
        )

    def test_fail_on_invalid_options(self):
        self.assert_pcs_fail(
            "booth ticket add TicketA site=a timeout=",
            (
                "Error: invalid booth ticket option 'site', allowed options"
                " are: 'acquire-after', 'attr-prereq', "
                "'before-acquire-handler', 'expire', 'renewal-freq', "
                "'retries', 'timeout', 'weights'\n"
                "Error: timeout cannot be empty\n"
                "Error: Errors have occurred, therefore pcs is unable to "
                "continue\n"
            ),
        )

    def test_forceable_fail_on_unknown_options(self):
        msg = (
            "invalid booth ticket option 'unknown', allowed options"
            " are: 'acquire-after', 'attr-prereq', 'before-acquire-handler',"
            " 'expire', 'renewal-freq', 'retries', 'timeout', 'weights'"
        )
        self.assert_pcs_fail(
            "booth ticket add TicketA unknown=a",
            (
                "Error: {0}, use --force to override\n"
                "Error: Errors have occurred, therefore pcs is unable to "
                "continue\n"
            ).format(msg),
        )
        self.assert_pcs_success(
            "booth ticket add TicketA unknown=a --force",
            "Warning: {0}\n".format(msg),
        )

    def test_not_enough_args(self):
        self.assert_pcs_fail(
            "booth ticket add",
            stdout_start="\nUsage: pcs booth <command>\n    ticket add",
        )


class DeleteRemoveTicketMixin:
    command = None

    def test_not_enough_args(self):
        self.assert_pcs_fail(
            f"booth ticket {self.command}",
            stdout_start=outdent(
                f"""
                Usage: pcs booth <command>
                    ticket {self.command} <"""
            ),
        )

    def test_too_many_args(self):
        self.assert_pcs_fail(
            f"booth ticket {self.command} aaa bbb",
            stdout_start=outdent(
                f"""
                Usage: pcs booth <command>
                    ticket {self.command} <"""
            ),
        )

    def test_success_remove_ticket(self):
        self.assert_pcs_success("booth ticket add TicketA")
        with open(self.booth_cfg_path, "r") as config_file:
            self.assertEqual(
                dedent(
                    """\
                    authfile = {0}
                    site = 1.1.1.1
                    site = 2.2.2.2
                    arbitrator = 3.3.3.3
                    ticket = "TicketA"
                    """.format(
                        self.booth_key_path
                    )
                ),
                config_file.read(),
            )
        self.assert_pcs_success(f"booth ticket {self.command} TicketA")
        with open(self.booth_cfg_path, "r") as config_file:
            self.assertEqual(
                dedent(
                    """\
                    authfile = {0}
                    site = 1.1.1.1
                    site = 2.2.2.2
                    arbitrator = 3.3.3.3
                    """.format(
                        self.booth_key_path
                    )
                ),
                config_file.read(),
            )

    def test_fail_when_ticket_does_not_exist(self):
        self.assert_pcs_fail(
            f"booth ticket {self.command} TicketA",
            (
                "Error: booth ticket name 'TicketA' does not exist\n"
                "Error: Errors have occurred, therefore pcs is unable to "
                "continue\n"
            ),
        )


class DeleteTicketTest(DeleteRemoveTicketMixin, BoothTest):
    command = "delete"


class RemoveTicketTest(DeleteRemoveTicketMixin, BoothTest):
    command = "remove"


@need_booth_resource_agent
class CreateTest(BoothMixinNoFiles, TestCase):
    def test_not_enough_args(self):
        self.assert_pcs_fail(
            "booth create",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    create ip <"""
            ),
        )
        self.assert_pcs_fail(
            "booth create ip",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    create ip <"""
            ),
        )

    def test_too_many_args(self):
        self.assert_pcs_fail(
            "booth create ip aaa bbb",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    create ip <"""
            ),
        )


class DeleteRemoveTestMixin(AssertPcsMixin):
    command = None

    def setUp(self):
        # pylint cannot know this will be mixed into a TetsCase class
        # pylint: disable=invalid-name
        self.temp_cib = get_tmp_file("tier1_booth_delete_remove")
        write_file_to_tmpfile(EMPTY_CIB, self.temp_cib)
        self.pcs_runner = PcsRunner(self.temp_cib.name)

    def tearDown(self):
        # pylint cannot possibly know this is being mixed into TestCase classes
        # pylint: disable=invalid-name
        self.temp_cib.close()

    def test_usage(self):
        self.assert_pcs_fail(
            f"booth {self.command} a b",
            stdout_start=outdent(
                f"""
                Usage: pcs booth <command>
                    {self.command}
                """
            ),
        )

    def test_failed_when_no_booth_configuration_created(self):
        self.assert_pcs_success("resource status", "NO resources configured\n")
        self.assert_pcs_fail(
            f"booth {self.command}",
            [
                # pylint: disable=line-too-long
                "Error: booth instance 'booth' not found in cib",
                "Error: Errors have occurred, therefore pcs is unable to continue",
            ],
        )


@need_booth_resource_agent
class DeleteTest(DeleteRemoveTestMixin, TestCase):
    command = "delete"


@need_booth_resource_agent
class RemoveTest(DeleteRemoveTestMixin, TestCase):
    command = "remove"


class TicketGrantTest(BoothMixinNoFiles, TestCase):
    def test_not_enough_args(self):
        self.assert_pcs_fail(
            "booth ticket grant",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    ticket grant <"""
            ),
        )

    def test_too_many_args(self):
        self.assert_pcs_fail(
            "booth ticket grant aaa bbb ccc",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    ticket grant <"""
            ),
        )


class TicketRevokeTest(BoothMixinNoFiles, TestCase):
    def test_not_enough_args(self):
        self.assert_pcs_fail(
            "booth ticket revoke",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    ticket revoke <"""
            ),
        )

    def test_too_many_args(self):
        self.assert_pcs_fail(
            "booth ticket revoke aaa bbb ccc",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    ticket revoke <"""
            ),
        )


class Restart(BoothMixinNoFiles, TestCase):
    def test_too_many_args(self):
        self.assert_pcs_fail(
            "booth restart aaa",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    restart"""
            ),
        )


class Sync(BoothMixinNoFiles, TestCase):
    def test_too_many_args(self):
        self.assert_pcs_fail(
            "booth sync aaa",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    sync"""
            ),
        )


class BoothServiceTestMixin(BoothMixinNoFiles):
    def test_too_many_args(self):
        self.assert_pcs_fail(
            f"booth {self.cmd_label} aaa",
            stdout_start=outdent(
                f"""
                Usage: pcs booth <command>
                    {self.cmd_label}"""
            ),
        )


class Enable(BoothServiceTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cmd_label = "enable"
        self.cli_cmd = booth_cmd.enable


class Disable(BoothServiceTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cmd_label = "disable"
        self.cli_cmd = booth_cmd.disable


class Start(BoothServiceTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cmd_label = "start"
        self.cli_cmd = booth_cmd.start


class Stop(BoothServiceTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cmd_label = "stop"
        self.cli_cmd = booth_cmd.stop


class Pull(BoothMixinNoFiles, TestCase):
    def test_not_enough_args(self):
        self.assert_pcs_fail(
            "booth pull",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    pull"""
            ),
        )

    def test_too_many_args(self):
        self.assert_pcs_fail(
            "booth pull aaa bbb",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    pull"""
            ),
        )


# disable printig the booth status so it won't break tests output
@mock.patch("pcs.cli.booth.command.print", new=lambda x: x)
class Status(BoothMixinNoFiles, TestCase):
    def test_too_many_args(self):
        self.assert_pcs_fail(
            "booth status aaa",
            stdout_start=outdent(
                """
                Usage: pcs booth <command>
                    status"""
            ),
        )
