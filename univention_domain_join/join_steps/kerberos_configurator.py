#!/usr/bin/env python
#
# Univention Domain Join
#
# Copyright 2017-2018 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

from shutil import copyfile
import logging
import os
import subprocess

from univention_domain_join.utils.general import execute_as_root

OUTPUT_SINK = open(os.devnull, 'w')

userinfo_logger = logging.getLogger('userinfo')


class ConflictChecker(object):
	def config_file_exists(self):
		if os.path.isfile('/etc/krb5.conf'):
			userinfo_logger.warn('Warning: /etc/krb5.conf already exists.')
			return True
		return False


class KerberosConfigurator(ConflictChecker):
	@execute_as_root
	def backup(self, backup_dir):
		if self.config_file_exists():
			if not os.path.exists(os.path.join(backup_dir, 'etc')):
				os.makedirs(os.path.join(backup_dir, 'etc'))
			copyfile(
				'/etc/krb5.conf',
				os.path.join(backup_dir, 'etc/krb5.conf')
			)

	def configure_kerberos(self, kerberos_realm, master_ip, ldap_master):
		self.write_config_file(kerberos_realm, master_ip, ldap_master)
		self.synchronize_time_with_master(ldap_master)

	@execute_as_root
	def write_config_file(self, kerberos_realm, master_ip, ldap_master):
		userinfo_logger.info('Writing /etc/krb5.conf ')

		config = \
			'[libdefaults]\n' \
			'    default_realm = %(kerberos_realm)s\n' \
			'    kdc_timesync = 1\n' \
			'    ccache_type = 4\n' \
			'    forwardable = true\n' \
			'    proxiable = true\n' \
			'    default_tkt_enctypes = arcfour-hmac-md5 des-cbc-md5 des3-hmac-sha1 des-cbc-crc des-cbc-md4 des3-cbc-sha1 aes128-cts-hmac-sha1-96 aes256-cts-hmac-sha1-96\n' \
			'    permitted_enctypes = des3-hmac-sha1 des-cbc-crc des-cbc-md4 des-cbc-md5 des3-cbc-sha1 arcfour-hmac-md5 aes128-cts-hmac-sha1-96 aes256-cts-hmac-sha1-96\n' \
			'    allow_weak_crypto=true\n' \
			'\n' \
			'[realms]\n' \
			'%(kerberos_realm)s = {\n' \
			'   kdc = %(master_ip)s $(ldap_master)s\n' \
			'   admin_server = %(master_ip)s %(ldap_master)s\n' \
			'   kpasswd_server = %(master_ip) %(ldap_master)s\n' \
			'}\n' \
			% {
				'kerberos_realm': kerberos_realm,
				'master_ip': master_ip,
				'ldap_master': ldap_master
			}

		with open('/etc/krb5.conf', 'w') as conf_file:
			conf_file.write(config)

	@execute_as_root
	def synchronize_time_with_master(self, ldap_master):
		userinfo_logger.info('Synchronizing time with the DC master')

		subprocess.check_call(
			['ntpdate', '-bu', ldap_master],
			stdout=OUTPUT_SINK, stderr=OUTPUT_SINK
		)
