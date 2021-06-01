#!/usr/bin/env python
import glob
import time
import urllib.request
import xml.etree.ElementTree

URL = "https://archlinux.org/feeds/releases/"
torrent_cache = '/srv/ISOs'

# Only run the grabber on the first of the month
if int(time.strftime("%d")) != 1:
	exit(0)

# Do we already have this months ISO?
if [filename for filename in glob.glob(torrent_cache+f"/*.torrent") if time.strftime('archlinux-%Y.%m.%d') in filename]:
	exit(0)

# Get the RSS feed for /releng/releases/
feed_response = urllib.request.urlopen(URL)
xml_data = feed_response.read()
xml_root = xml.etree.ElementTree.fromstring(xml_data.decode('utf-8'))

# xml_tree = xml.etree.ElementTree.parse('test.xml')
# xml_root = xml_tree.getroot()

if xml_root.tag == 'rss':
	for item in xml_root[0].iter('item'):
		torrent_url = list(item.iter('enclosure'))[0].get('url')

		torrent_response = urllib.request.urlopen(torrent_url)

		# Extract the filename:
		#   (Header example) Content-Disposition: attachment; filename=archlinux-2021.05.01-x86_64.iso.torrent
		filename = torrent_response.getheader('Content-Disposition').split(';')[-1].split('=', 1)[1].strip()
		if not '.torrent' in filename:
			raise ValueError(f"File type is not a torrent: {filename}")

		# Save the .torrent in the torrent-cache directory
		with open(torrent_cache+f"/{filename}", "wb") as torrent_fh:
			torrent_fh.write(torrent_response.read())
