#!/bin/sh

set -e

kexec_set_config()
{
	# Skip unless running on Debian or a derivative.
	if [ ! -f '/etc/debian_version' ]; then
		return
	fi

	local conffile='/etc/default/kexec'
	local newconf="$(mktemp -- "$conffile.sp-dep.XXXXXX")"

	echo "Trying to set the kexec configuration variables in $conffile"

	perl -pe 's/^\s*LOAD_KEXEC\s*=.*/LOAD_KEXEC=true/; s/^\s*USE_GRUB_CONFIG\s*=.*/USE_GRUB_CONFIG=false/' < "$conffile" > "$newconf" || (rm -f -- "$newconf"; false)

	mv -- "$newconf" "$conffile" || (rm -f -- "$newconf"; false)

	debconf-set-selections <<'EODEBCONF'
kexec-tools	kexec-tools/load_kexec	boolean	true
kexec-tools	kexec-tools/use_grub_config	boolean	false
EODEBCONF

	echo 'Rerunning the kexec-tools configure step'
	env \
		DEBIAN_FRONTEND=noninteractive \
		DPKG_HOOK_ACTION=configure \
		DPKG_MAINTSCRIPT_PACKAGE=kexec-tools \
		DPKG_MAINTSCRIPT_PACKAGE_REFCOUNT=1 \
		DPKG_MAINTSCRIPT_ARCH="$(uname -m)" \
		DPKG_MAINTSCRIPT_NAME=postinst \
		/var/lib/dpkg/info/kexec-tools.postinst configure

	echo 'Making sure it caught...'
	egrep -e '^(LOAD_KEXEC|USE_GRUB_CONFIG)=' -- "$conffile"
	egrep -qe '^LOAD_KEXEC=true' -- "$conffile"
	egrep -qe '^USE_GRUB_CONFIG=false' -- "$conffile"

	echo 'Looks fine!'
}

resolvedeps()
{
	local pkgfile='resolvedeps-pkg.txt'
	local depfile='resolvedeps-dep.txt'
	local pkg dep deplocal

	: > "$pkgfile"
	for pkg; do
		printf '%s\n' "$pkg" >> "$pkgfile"

		rpm -qpR -- "$pkg" | (egrep -e '^storpool-.*-dep-' > "$depfile" || true)

		for dep in $(cat -- "$depfile"); do
			deplocal="$(find . -mindepth 1 -maxdepth 1 -type f -name "${dep}*.rpm" || true)"
			if [ -f "$deplocal" ]; then
				printf '%s\n' "$deplocal" >> "$pkgfile"
			fi
		done
	done

	sort -u -- "$pkgfile" | xargs
	rm -f -- "$pkgfile" "$depfile"
}

if [ "$#" -eq 0 ]; then
	cat <<'EOUSAGE' 1>&2
Usage: install-packages type...
Examples:
	install-packages install
	install-packages config common block
EOUSAGE
	exit 1
fi

packages=''
while [ "$#" -gt 0 ]; do
	tag="$1"
	shift

	namefile="package-$tag-dep.txt"
	if [ ! -f "$namefile" ]; then
		echo "No package filename file '$namefile' for tag '$tag'" 1>&2
		exit 1
	fi
	pkgfile="$(cat -- "$namefile")"
	if [ ! -f "$pkgfile" ]; then
		echo "No package file '$pkgfile' for tag '$tag'" 1>&2
		exit 1
	fi

	packages="$packages ./$pkgfile"
done

while true; do
	npkg="$(resolvedeps $packages)"
	if [ "$npkg" = "$packages" ]; then
		break
	fi
	packages="$npkg"
done

if [ -z "$packages" ]; then
	echo 'Internal error: no packages to install' 1>&2
	exit 1
fi

if [ -f '/etc/debian_version' ]; then
	had_kexec_tools="$(dpkg-query -W -f '${Version}\n' kexec-tools || true)"
else
	had_kexec_tools=''
fi

./add-storpool-repo.sh

unset to_install to_reinstall
for f in $packages; do
	package="$(rpm -qp "$f")"
	if rpm -q -- "$package"; then
		to_reinstall="$to_reinstall ./$f"
	else
		to_install="$to_install ./$f"
	fi
done

if [ -n "$to_install" ]; then
	yum install -y --enablerepo=storpool-contrib -- $to_install
fi
if [ -n "$to_reinstall" ]; then
	yum reinstall -y --enablerepo=storpool-contrib -- $to_reinstall
fi


if [ -f '/etc/debian_version' ]; then
	have_kexec_tools="$(dpkg-query -W -f '${Version}\n' kexec-tools || true)"
else
	have_kexec_tools=''
fi

# OK, this is a kind of a hack, but whatever
if [ -z "$had_kexec_tools" ] && [ -n "$have_kexec_tools" ]; then
	kexec_set_config
fi
