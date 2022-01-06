import discum
import requests 
import base64
import time
import threading

# to join the server
DOES_JOIN = True
SERVER_INVITE = ""

# settings for pfp change
CHANGE_PFP = True
IMAGE = ""

# settings for username change
CHANGE_USERNAME = True
USERNAME = ""

# settings for mass dm
MESSAGE = ""
SERVER_ID = ""
CHANNEL_ID = ""

# api
CREATE_DM = "https://discord.com/api/v9/users/@me/channels"
SCIENCE = "https://discord.com/api/v9/science"
SEND_MESSAGE_API = "https://discord.com/api/v9/channels/{}/messages"
CHANGE_USER_API = "https://discord.com/api/v9/users/@me"
JOIN_SERVER_API = "https://discord.com/api/v9/invites/{}"

#
proxies = {
	"https" : "",
	"http" : ""}

disabled_userbots = {}
userbots_in_use = 0
desired_bots_in_use = 3

email_index = 0
pw_index = 1
token_index = 2

# f
def init_userbot(auth):
	try:
		token = auth[token_index]
		password = auth[pw_index]
		headers = {"authorization": token, "Content-Type": "application/json", "Host": "discord.com"}
		if DOES_JOIN:
			r = requests.post(JOIN_SERVER_API.format(SERVER_INVITE), headers=headers, json={}, proxies=proxies)
			print("\nJoined Server - Status Code of {}\n".format(r.status_code))

		if CHANGE_PFP:
			base64img = ""
			with open(IMAGE, "rb") as img_file:
				base64img = base64.b64encode(img_file.read()).decode('utf-8')

			data = {"avatar": "data:image/png;base64,{}".format(base64img)} 
			r = requests.patch(CHANGE_USER_API, json=data, headers=headers, proxies=proxies)
			print("\nChanged Icon - Status Code of {} - Reponse Body of {}\n".format(r.status_code, r.text))

		if CHANGE_USERNAME:
			data = {"username": USERNAME, "password": password}
			r = requests.patch(CHANGE_USER_API, json=data, headers=headers, proxies=proxies)
			print("\nChanged Username - Status Code of {} - Response Body of {}\n".format(r.status_code, r.text))
	except Exception as e:
		time.sleep(0.5)
		init_userbot(auth)

def init_msging(token):
	def msg(id):
		try:
			headers = {"authorization": token, "Content-Type": "application/json", "Host": "discord.com"}

			cr_data = {"recipients" : [id]}
			r_creation = requests.post(CREATE_DM, json=cr_data, headers=headers, proxies=proxies)
			print("\nCreated DM Channel with {} - Status Code of {} - Response Body of {}\n".format(id, r_creation.status_code, r_creation.text))
			
			json = r_creation.json()
			channel_id = "id" in json and json["id"] or False
			if channel_id:
				api = SEND_MESSAGE_API.format(channel_id)
				data = {"content" : MESSAGE, "tts": False}
				r = requests.post(api, json=data, headers=headers, proxies=proxies)
				print("\nSent message to {} - Status Code of {} - Response Body of {}\n".format(id, r.status_code, r.text))
			else:
				print("Error when sending message! - Token of ({}) - Id of ({})".format(token, id))

				if r_creation.status_code == 401 or r_creation.status_code == 403: #-- Userbot got disabled, stop using it.
					disabled_userbots[token] = True
					print("Token of ({}) was disabled. Total of {} bots disabled now.".format(token, len(disabled_userbots)))
		except Exception as e:
			time.sleep(0.5)
			msg(id)

	return msg

# main
with open("authentications","r") as f:
	authentications = [x[:-1].split(":") for x in f.readlines()][:-1]

	#-- Send test message to vert
	_test_auth = authentications.pop()
	_test_token = _test_auth[token_index]
	init_userbot(_test_auth)

	#-- Grab member list
	bot = discum.Client(token=_test_token)

	def close_after_fetching(resp, guild_id):
		if bot.gateway.finishedMemberFetching(guild_id):
			lenmembersfetched = len(bot.gateway.session.guild(guild_id).members) 
			print(str(lenmembersfetched)+' members fetched') 
			bot.gateway.removeCommand({'function': close_after_fetching, 'params': {'guild_id': guild_id}})
			bot.gateway.close()

	def get_members(guild_id, channel_id):
		bot.gateway.fetchMembers(guild_id, channel_id, keep="all", wait=1)
		bot.gateway.command({'function': close_after_fetching, 'params': {'guild_id': guild_id}})
		bot.gateway.run()
		bot.gateway.resetSession()
		return bot.gateway.session.guild(guild_id).members

	members = list(get_members(SERVER_ID, CHANNEL_ID))

	#-- 
	threads = []
	in_use = []
	counter = 0
	while 10*counter < len(members):
		init = time.time()
		while userbots_in_use < desired_bots_in_use:
			userbots_in_use+=1
			auth = authentications.pop()
			thread = threading.Thread(target=init_userbot, args=(auth,))
			thread.daemon = True
			thread.start()
			threads.append(thread)

			in_use.append(auth)

			time.sleep(0.01)
			threads = []

		for t in threads:
			t.join()

		threads = []

		for auth in in_use:
			token = auth[token_index]
			if token not in disabled_userbots:
				counter+=1

				end = len(members) > 10*counter and 10*counter or len(members)
				ids = members[10*(counter-1):end]

				msg = init_msging(token)

				for id in ids:
					thread = threading.Thread(target=msg, args=(id,))
					thread.daemon = True
					thread.start()

				if end == len(members):
					print("Completed.")
					break;
			else:
				in_use.remove(auth)
				userbots_in_use-=1


		print("Sleeping for {:.0f} seconds.".format(600-(time.time()-init)))
		time.sleep(1)
