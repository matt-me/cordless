import discord
import asyncio
import copy
import rethinkdb as r
client = discord.Client()
idiot_proof = True
server_configs = {}
emojis = ["📗", "📘", "📙", "📓", "📒", "🔋", "🔮", "💣",
    "🏹", "🗡", "⛏", "🎵", "🎲", "🏀", "👑", "🎁", "🚗", "🌍", "🚩"]


def idiot_proof_perms(permissions):
    return (permissions.administrator or permissions.manage_channels or permissions.manage_server or permissions.ban_members or permissions.kick_members or permissions.mention_everyone)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    # add getting config from a database here
    for server in client.servers:
        if server_configs.get(server.id, None) is None:
            server_configs[server.id] = ServerConfig(server.id)
    

@client.event
async def on_message(message):
    if client.user.mentioned_in(message) and message.author.id != client.user.id and not message.channel.is_private:
        await run_command(message, message.channel, message.author)

@client.event
async def on_member_join(member):
    if server_configs[member.server.id].welcome_channel is not None and len(server_configs[member.server.id].welcome_msg) > 0:
        await client.send_message(server_configs[member.server.id].welcome_channel, server_configs[member.server.id].welcome_msg)

@client.event
async def on_member_leave(member):
    if server_configs[member.server.id].welcome_channel is not None and len(server_configs[member.server.id].welcome_msg) > 0:
        await client.send_message(server_configs[member.server.id].welcome_channel, server_configs[member.server.id].welcome_msg)


async def run_command(message, channel, user):
    config = server_configs[message.server.id]
    print(message.author.name + "[" + message.author.id + "]" + " : " + message.content.lower())
    debug_channel = server_configs[message.server.id].debug_channel
    if debug_channel is not None:
        await client.send_message(debug_channel, message.author.name + "[" + message.author.id + "]" + " : " + message.content.lower())
    if "help" in message.content.lower():
        await client.send_message(message.author, "I currently support the following commands:\n\n**rolelist** - setup a list of roles that users can react to\n**private** - allows you to execute commands in the channel by pming them to me instead of saying them out loud\n**backup** - backs up the server, preserving channels, permissions, and roles\n**possess** - allows you to speak as me by pming me what you want me to say\n**setwelcome <message>** - sets the welcome message for the server on the current channel\n**setgoodbye <message>** - sets a goodbye message to play when someone leaves\n\n\nTo execute any of these commands, just ping me.")
    elif "private" in message.content.lower():
        if existing = getConversation(config.conversations, user, user)
        if existing is not None:
            existing.task.cancel()
            config.conversations.remove(existing)
        config.conversations.append(Conversation(message.user, message, "Opened private conversation"))
        await client.send_message(message.author, "Opened a private channel. Commands will be relayed to " + message.server.name + "** in channel #" + message.channel.name)
    elif "backup" in message.content.lower():
        await backup_server(message.server)
    elif "possess" in message.content.lower():
        # first terminate any existing possessions of this user
        existing = getConversation(config.conversations, user, user)
        if existing is not None:
            existing.task.cancel()
            config.conversations.remove(existing)
        convo = config.conversations.append(Conversation(user, message, "Possessing this bot"))
        await client.send_message(message.author, "You have now taken control of me. Any messages you send in this private chat will be relayed to server **" + message.server.name + "** in channel #" + message.channel.name + "\nTo terminate this connection, please react to the above message")
        convo.task = asyncio.ensure_future(possess_loop(message.author, message.channel))
    elif "showconfig" in message.content.lower():
        await client.send_message(message.channel, "**Server configuration**\nI am keeping track of " + str(len(config.conversations)) + " conversations.\nI have ")
    elif "setwelcome" in message.content.lower():
        index = message.content.find("setwelcome") + len("setwelcome") + 1
        config.welcome_msg = message.content[index:]
        config.welcome_channel = message.channel
        await client.add_reaction(message, "✅")
    elif "setgoodbye" in message.content.lower():
        index = message.content.find("setgoodbye") + len("setgoodbye") + 1
        config.welcome_msg = message.content[index:]
        config.welcome_channel = message.channel
        await client.add_reaction(message, "✅")
    elif "debug" in message.content.lower():
        config.debug_channel = channel
    elif "rolelist" in message.content.lower():
        total_roles = message.server.roles
        emoji_iterator = iter(emojis)
        react_message = ReactionRoleMessage()
        emoji_list = []
        for role in total_roles:
            print(role.name)
            if (not role.is_everyone and (not idiot_proof or not idiot_proof_perms(role.permissions))):
                reaction = next(emoji_iterator)
                emoji_list.append(reaction)
                react_message.addLine(reaction, role)
        react_message.message = await client.send_message(message.channel, react_message.getText())
        example = react_message.getExample()
        stray_messages = []
        stray_messages.append(await client.send_message(message.channel, message.author.mention + " Next: Are there any roles that shouldn't be on this list? Remove them now by reacting to the above message. For example, to remove role **" + example[0] + "** from the list, react with " + example[1]))
        stray_messages.append(await client.send_message(message.channel, "When you're finished, just say 'done'"))
        conversation = Conversation(message.author, react_message.message, "Deleting roles from list")
        config.conversations.append(conversation)
        for emote in emoji_list:
            await client.add_reaction(react_message.message, emote)
        try:
            remover = asyncio.ensure_future(format_rolelist_loop(react_message))
            stray_messages.append(await client.wait_for_message(timeout=60 * 5, author=message.author, channel=message.channel, content="done"))
        except asyncio.TimeoutError:
            return
        finally:
            remover.cancel()
            config.conversations.remove(conversation)
            await client.delete_messages(iter(stray_messages))
            react_message.active = True
            asyncio.ensure_future(give_role_loop(react_message))

async def possess_loop(user, channel):
    while(True):
        try:
            message = await client.wait_for_message(timeout=60 * 5, author=user)
        except asyncio.TimeoutError:
            return
        if (message.channel.is_private):
            await client.send_message(channel, message.content)

async def give_role_loop(msg):
    while(client.get_message(msg.message.channel, msg.message.id)):
        res = await client.wait_for_reaction(message=msg.message)
        while(res.user.id == client.user.id):
            res = await client.wait_for_reaction(message=msg.message)
        role = msg.role_dict[res.reaction.emoji][1]
        if role.permissions.administrator:
            print("ALERT! " + res.user.name + " tried to get role " + role.name + " which has administrative privileges!")
        else:
            await client.add_roles(res.user, role)

async def remove_role_loop(msg):
    while(client.get_message(msg.message.channel, msg.message.id)):
        res = await client.wait_for_reaction(message=msg.message)
        while(res.user.id == client.user.id):
            res = await client.wait_for_reaction(message=msg.message)
        role = msg.role_dict[res.reaction.emoji][1]
        if role.permissions.administrator:
            print("ALERT! " + res.user.name + " tried to remove role " + role.name + " which has administrative privileges!")
        else:
            await client.remove_roles(res.user, role)

async def format_rolelist_loop(msg):
    config = server_configs[msg.message.server.id]
    while(client.get_message(msg.message.channel, msg.message.id)):
        res = await client.wait_for_reaction(message=msg.message)
        while(res.user.id == client.user.id):
            res = await client.wait_for_reaction(message=msg.message)
        reaction = res.reaction
        user = res.user
        conversation = getConversation(config.conversations, reaction.message, user)
        react_message = msg
        if conversation is not None and conversation.description == "Deleting roles from list":
            react_message.removeLine(reaction.emoji)
            await client.edit_message(reaction.message, new_content=react_message.getText())
            await client.remove_reaction(reaction.message, reaction.emoji, client.user)
            await client.remove_reaction(reaction.message, reaction.emoji, user)
        else:
            return

async def backup_server(server):
    config = server_configs[server.id]
    user_roles = {}
    config.role_backup[server.id] = user_roles
    await client.request_offline_members(server)
    count = 0
    for member in server.members:
        user_roles[member.id] = member.roles
        for role in member.roles:
            print("Giving " + member.name + " the role" + role.name)
        count += 1
    print(str(count) + " users backed up.")
    count = 0
    config.channel_backup[server.id] = []
    for channel in server.channels:
        print("Backing up #" + channel.name)
        config.channel_backup[server.id].append(channel)
        count += 1
    print(str(count) + " channels backed up.")

def getConversation(conversations, channel, user):
    for conversation in conversations:
        if conversation.user.id == user.id and conversation.last_message.id == channel.id:
            return conversation
    return None

class Conversation:
    def __init__(self, user, last_message, description):
        self.user = user
        self.last_message = last_message
        self.description = description
        self.task = None
    def __eq__(self, other):
        return (self.user == other.user and self.last_message == other.last_message and self.description == other.description)

class ReactionRoleMessage:
    def __init__(self):
        self.message = None
        self.role_dict = {}
        self.active = False
    def addLine(self, reaction, role):
        value = ["React with " + \
            reaction + " for role " + role.name + "\n", role]
        self.role_dict[reaction] = value

    def removeLine(self, reaction):
        del self.role_dict[reaction]

    def getText(self):
        result = ""
        for line in list(self.role_dict.values()):
            result += line[0]
        return result
        
    def getExample(self):
        return [list(self.role_dict.values())[0][1].name, list(self.role_dict.keys())[0]]

class ServerConfig:
    def __init__(self, id):
        self.serverid = id
        self.role_backup = {}
        self.conversations = []
        self.tasks = []
        self.role_backup = {}
        self.channel_backup = {}
        self.welcome_msg = ""
        self.welcome_channel = None
        self.goodbye_msg = ""
        self.debug_channel = None

r.connect(host="127.0.0.1", port=28015).repl()
client.run('NTI3OTA2OTc0MTkzNTQ5MzE0.DwmAqg.x-GYbJSWrQiNfYEZmBMEFkmVoFs')
