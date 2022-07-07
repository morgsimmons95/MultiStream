
#import libraries
import vlc
import sys
import json
import os
import pathlib
from threading import Thread, Event
import time
import platform
from os.path import expanduser
from ttkbootstrap import Style

#switch imports on python version
if sys.version_info[0] < 3:
	import Tkinter as Tk
	from Tkinter import *
	from Tkinter import ttk
	from Tkinter.filedialog import askopenfilename
	from Tkinter.messagebox import showerror, askyesno, showinfo
else:
	import tkinter as Tk
	from tkinter import *
	from tkinter import ttk
	from tkinter.filedialog import askopenfilename
	from tkinter.messagebox import showerror, askyesno, showinfo

#######################################################################################################################################################################################################
#About section info
vers = "1.1"
bio = "Version {}\nDeveloped by Morgan Simmons, DC3".format(vers)

#######################################################################################################################################################################################################
#backend datatype for streams
class stream:
	
	#no arguments are required for object instantiation
	def __init__(self, name = None, mrl = None, server = None):
		self.name = name
		self.mrl = mrl
		self.server = server

#######################################################################################################################################################################################################
#primary gui datatype - this is the only object created in main.py
#not explicitly singleton but effectively singleton
class LAPCStream(Frame):
		
	#class attribute to indicate which stream object is currently attached to the media_player object (by title)
	currently_playing = ''

	#init function
	def __init__(self, top=None, video=''):
		
		#configure primary gui frame
		Frame.__init__(self, top)
		self.parent = top
		self.parent.title("DMED MultiStream")
		self.video = expanduser(video)
		self.parent.geometry("1480x720")
		self.style = Style(theme='darkly')

		#configure menu bar
		self.menubar = Menu(top,font="TkMenuFont")
		top.configure(menu = self.menubar)
		self.sub_menu = Menu(top,tearoff=0)
		self.menubar.add_command(
						label="End Current Stream",
						command = lambda: end_stream(self))
		self.menubar.add_command(
						label="Manage",
						command = lambda: open_manage(self))
		self.menubar.add_command(
						label="About",
						command = lambda: about(bio))								
		self.menubar.add_command(
						label="Quit",
						command = _quit)

		#instantiate and configure "channel guide" listbox
		self.ListBox1 = Listbox(self.parent)
		self.ListBox1.configure(exportselection=0)
		self.ListBox1.place(relx=0.006, rely=0.036, relheight=0.957, relwidth=0.121)
		self.ListBox1.bind('<Double-Button-1>', lambda evt: stream_select(self ,self.ListBox1.get(self.ListBox1.curselection())))
		self.ListBox1.bind('<Return>', lambda evt: stream_select(self ,self.ListBox1.get(self.ListBox1.curselection())))
	
		#configure videopanel frame object
		self.videopanel = ttk.Frame(self.parent)
		self.videopanel.place(relx=0.13, rely=0.0, relheight=0.992, relwidth=0.865)

		#label
		self.Label1 = Label(self.parent)
		self.Label1.place(relx=0.006, rely=0.006, height=21, width=104)
		self.Label1.configure(text='Available Streams')	

		#configure VLC plugin player
		args = []
		self.Instance = vlc.Instance(args)
		self.player = self.Instance.media_player_new()
		if platform.system() == 'Windows':
			self.player.set_hwnd(self.videopanel.winfo_id())
		populateStored(self) 		
		self.parent.update()		

		#start application with the ESPN stream
		storedStreams = getStored(self)
		espn = storedStreams['streams']['1']
		stream_select(self, espn['title'])
		
	
	#class function -- is this ever used?
	def setTitle(self, nettitle):
		self.menubar.config(title = nettitle)

#######################################################################################################################################################################################################
#gui datatype for manipulating streams.json file (in lieu of a database)
#this class will be removed in the user-only version
#explicitly singleton
class Manage_Window:
	#singleton attribute
	__instance = None

	#function to manage singleton - helper function to return object id
	def singleton(self):
		return id(self)

	#function to delete singleton instance attribute
	def clear(self):
		Manage_Window.__instance = None

	#in manage window, this function populates the streams listbox
	def showList(self):
		streamData = getStored(self)
		self.Listbox1.delete(0, END)
		for item in streamData['streams']:
			self.Listbox1.insert(END, streamData['streams'][item]['title'])

	#in manage window, this function clears away the data in the entries and combobox - used after delete or on mw creation
	def clearDetails(self):
		self.Entry1.configure(state=NORMAL)
		self.Entry1.delete(0, END)
		self.Entry2.configure(state=NORMAL)
		self.Entry2.delete(0, END)
		self.Entry3.configure(state=NORMAL)
		self.Entry3.delete(0, END)
		self.TCombobox1['state'] = 'normal'
		self.TCombobox1.delete(0, END)
		
	#in manage window, this function populates the entries and combobox - used after selecting a stream in the listbox
	def showDetails(self, selText):
		streamData = getStored(self)
		for item in streamData['streams']:
			if streamData['streams'][item]['title'] == selText:
				details = streamData['streams'][item]
				break	
		
		self.Entry1.configure(state=NORMAL)
		self.Entry1.delete(0, END)
		self.Entry1.insert(END, selText)
		self.Entry1.configure(state=DISABLED)
		
		self.Entry2.configure(state=NORMAL)
		self.Entry2.delete(0, END)
		self.Entry2.insert(END, details["ip"])
		self.Entry2.configure(state=DISABLED)

		self.Entry3.configure(state=NORMAL)
		self.Entry3.delete(0, END)
		self.Entry3.insert(END, details["port"])
		self.Entry3.configure(state=DISABLED)

		if details["protocol"] in self.TCombobox1['values']:
			self.TCombobox1.set(details["protocol"])

		self.Button2.configure(state=NORMAL)
		self.Button3.configure(state=NORMAL)

	#in manage window, this function unlocks the entries and combobox so the data can be edited - called after edit button is triggered
	def editDetails(self, selText):
		self.Entry1.configure(state=NORMAL)
		self.Entry2.configure(state=NORMAL)
		self.Entry3.configure(state=NORMAL)
		self.TCombobox1['state'] = 'readonly'
		self.Button1.configure(state=DISABLED)
		self.Button2.configure(state=NORMAL)
		self.Button3.configure(state=DISABLED)
		self.Button4.configure(state=NORMAL)

		self.Button2.configure(text="Cancel")
		self.Button2.configure(command = self.cancelDetails)

	#in manage window, this function locks the entries and comboboxes so the data cannot be edited - called after the cancel button is triggered (which is only possible after the edit button is triggered)
	def cancelDetails(self):
		self.clearDetails()
		self.Listbox1.configure(state=NORMAL)
		self.Entry1.configure(state=DISABLED)
		self.Entry2.configure(state=DISABLED)
		self.Entry3.configure(state=DISABLED)
		self.TCombobox1['state'] = 'disabled'
		self.Button1.configure(state=NORMAL)
		self.Button2.configure(state=DISABLED)
		self.Button3.configure(state=DISABLED)
		self.Button4.configure(state=DISABLED)

		self.Button2.configure(text='Edit')
		self.Button2.configure(command=lambda: self.editDetails(self.Listbox1.get(self.Listbox1.curselection())))

		self.showList()

	#in manage window, this function saves the edited entry and combobox data to the streams.json file
	def saveDetails(self, selText):
		storedStreams = getStored(self)['streams']
		for item in storedStreams:
			if storedStreams[item]['title'] == selText:
				streamID = item
				streamDetails = {item:storedStreams[item]}
				storedStreams.pop(item)
				break
		
		duplicate = False

		newTitle = self.Entry1.get()
		newIP = self.Entry2.get()
		newPort = self.Entry3.get()
		newProtocol = self.TCombobox1.get()

		newDetails = {streamID: {}}

		for item in storedStreams:
			if storedStreams[item]['title'] == newTitle:
				duplicate = True
				self.alert("A stream with this title already exists.")
				break
			if storedStreams[item]['ip'] == newIP:
				duplicate = True
				self.alert("A stream with this IP address already exists.")
				break


		if not duplicate:
			newDetails[streamID]['title'] = newTitle
			newDetails[streamID]['ip'] = newIP
			newDetails[streamID]['port'] = newPort
			newDetails[streamID]['protocol'] = newProtocol
			
			storedStreams[streamID] = newDetails[streamID]
			newJSON = getStored(self)
			newJSON['streams'] = storedStreams
			with open('streams.json', 'w') as outfile:
				json.dump(newJSON, outfile)		#does not pretty print?
			self.cancelDetails()
		
	#in manage window, this function creates a new window object with entries and a combobox to add a new stream's data to the streams.json file
	def addWindow(self):
		new = Toplevel(Tk_get_root())
		new.geometry("360x225")
		new.minsize(120, 1)
		new.maxsize(3844, 2141)
		new.resizable(0, 0)
		new.title("New Stream")

		new.Entry1 = Entry(new)
		new.Entry1.place(relx=0.222, rely=0.089,height=20, relwidth=0.733)

		new.Entry2 = Entry(new)
		new.Entry2.place(relx=0.222, rely=0.267,height=20, relwidth=0.733)

		new.Entry3 = Entry(new)
		new.Entry3.place(relx=0.222, rely=0.444,height=20, relwidth=0.206)

		new.TCombobox1 = ttk.Combobox(new)
		new.TCombobox1.place(relx=0.222, rely=0.622, relheight=0.093, relwidth=0.203)
		new.TCombobox1['values'] = ('udp', 'rtp', 'http')
		new.TCombobox1['state'] = 'readonly'

		new.Label1 = Label(new)
		new.Label1.place(relx=0.056, rely=0.089, height=21, width=54)
		new.Label1.configure(text='''Title:''')

		new.Label2 = Label(new)
		new.Label2.place(relx=0.056, rely=0.267, height=21, width=54)
		new.Label2.configure(text='''IP:''')

		new.Label3 = Label(new)
		new.Label3.place(relx=0.056, rely=0.444, height=21, width=54)
		new.Label3.configure(text='''Port:''')

		new.Label5 = Label(new)
		new.Label5.place(relx=0.056, rely=0.622, height=21, width=54)
		new.Label5.configure(text='''Protocol:''')

		new.Button1 = Button(new)
		new.Button1.place(relx=0.056, rely=0.8, height=24, width=147)
		new.Button1.configure(text='''Add''')
		new.Button1.configure(command=lambda: self.addStore(new))

		new.Button2 = Button(new)
		new.Button2.place(relx=0.528, rely=0.8, height=24, width=147)
		new.Button2.configure(text='''Cancel''')
		new.Button2.configure(command=lambda: new.destroy())

		new.grab_set()

	#in manage window, this function actually saves the stream data entered into the addWindow to the streams.json file
	def addStore(self, window):
		title = window.Entry1.get()
		ip = window.Entry2.get()
		port = window.Entry3.get()
		protocol = window.TCombobox1.get()

		newJSON = getStored(self)
		storedStreams = newJSON['streams']
		newStreamID = int(newJSON['next_id'])
		newDetails = {newStreamID: {}}

		for item in storedStreams:
			if storedStreams[item]['title'] == title:
				alert('A stream with this title already exists.')
				return
			if storedStreams[item]['ip'] == ip:
				alert('A stream with this IP address already exists.')
				return

		if title:
			newDetails[newStreamID]['title'] = title
		else:
			alert('A title is required.')
			return
		if ip:
			newDetails[newStreamID]['ip'] = ip
		else:
			alert('An ip address is required.')
			return
		if port:
			newDetails[newStreamID]['port'] = port
		else:
			newDetails[newStreamID]['port'] = ''
		if protocol:
			newDetails[newStreamID]['protocol'] = protocol
		else:
			alert('A protocol is required.')
			return

		newJSON['next_id'] = str(int(newJSON['next_id'])+1)
		storedStreams[newStreamID] = newDetails[newStreamID]
		newJSON['streams'] = storedStreams
		with open('streams.json', 'w') as outfile:
			json.dump(newJSON, outfile)
		outfile.close()
		window.destroy()
		self.cancelDetails()

	#in manage window, this function creates a new window object to confirm deletion of a selected stream
	def deleteWindow(self):

		selection = str(self.Listbox1.get(self.Listbox1.curselection()))
		msg = "Are you sure you want to delete " + selection + '?'
		res = askyesno('Delete', msg, parent=self.Button3)
		if res:
			self.deleteStore(selection)
		else:
			pass

	#in manage window, this function actually deletes the stream selected in the listbox from the streams.json file
	def deleteStore(self, selection):
		storedStreams = getStored(self)
		newJSON = storedStreams['streams']
		for item in newJSON:
			if newJSON[item]['title'] == selection:
				newJSON.pop(item)
				break
		storedStreams['streams'] = newJSON
		#window.destroy()
		with open('streams.json', 'w') as outfile:
			json.dump(storedStreams, outfile)
		outfile.close()
		self.cancelDetails()

	#init function
	def __init__(self, parent):
		#singleton
		if Manage_Window.__instance is None:
			Manage_Window.__instance = Manage_Window.singleton(self)

			#configure manage window frame
			new = Toplevel(Tk_get_root())
			new.geometry("600x300")
			new.minsize(120, 1)
			new.maxsize(3844, 2141)
			new.resizable(1, 1)
			new.title("Manage Streams")
			new.style = Style(theme='darkly')	


			#what to do when [x] is clicked on manage window
			new.protocol('WM_DELETE_WINDOW', lambda: Manage_Window.clear(self) or new.destroy() or populateStored(parent))


			#configure listbox
			self.Listbox1 = Listbox(new, exportselection=False)
			self.Listbox1.place(relx=0.017, rely=0.1, relheight=0.85, relwidth=0.418)
			self.Listbox1.bind('<<ListboxSelect>>', lambda evt: self.showDetails(self.Listbox1.get(self.Listbox1.curselection())))

			#configure streams label
			self.TLabel1 = ttk.Label(new)
			self.TLabel1.place(relx=0.017, rely=0.033, height=19, width=46)
			self.TLabel1.configure(text='''Streams''')

			#configure separator
			self.TSeparator1 = ttk.Separator(new)
			self.TSeparator1.place(relx=0.467, rely=0.1, relheight=0.833)
			self.TSeparator1.configure(orient="vertical")

			#configure entries
			self.Entry1 = Entry(new)
			self.Entry1.place(relx=0.583, rely=0.133,height=20, relwidth=0.39)
			self.Entry1.configure(state=DISABLED)

			self.Entry2 = Entry(new)
			self.Entry2.place(relx=0.583, rely=0.267,height=20, relwidth=0.39)
			self.Entry2.configure(state=DISABLED)

			self.Entry3 = Entry(new)
			self.Entry3.place(relx=0.583, rely=0.4,height=20, relwidth=0.14)
			self.Entry3.configure(state=DISABLED)

			#configure combobox for protocol
			self.TCombobox1 = ttk.Combobox(new)
			self.TCombobox1.place(relx=0.583, rely=0.533, relheight=0.087, relwidth=0.14)
			self.TCombobox1.configure(takefocus="")
			self.TCombobox1['state'] = 'disabled'
			self.TCombobox1['values'] = ('udp', 'rtp', 'http')

			#configure separator
			self.TSeparator2 = ttk.Separator(new)
			self.TSeparator2.place(relx=0.483, rely=0.667, relwidth=0.483)

			#configure add, edit, delete, and save buttons
			self.Button1 = Button(new)
			self.Button1.place(relx=0.512, rely=0.7, height=24, width=127)
			self.Button1.configure(text='''Add...''')
			self.Button1.configure(state=NORMAL)
			self.Button1.configure(command=lambda: self.addWindow())

			self.Button2 = Button(new)
			self.Button2.place(relx=0.75, rely=0.7, height=24, width=127)
			self.Button2.configure(text='''Edit''')
			self.Button2.configure(state=DISABLED)
			self.Button2.configure(command=lambda: self.editDetails(self.Listbox1.get(self.Listbox1.curselection())))

			self.Button3 = Button(new)
			self.Button3.place(relx=0.512, rely=0.833, height=24, width=127)
			self.Button3.configure(text='''Delete...''')
			self.Button3.configure(state=DISABLED)
			self.Button3.configure(command=lambda: self.deleteWindow())

			self.Button4 = Button(new)
			self.Button4.place(relx=0.75, rely=0.833, height=24, width=127)
			self.Button4.configure(text='''Save''')
			self.Button4.configure(state=DISABLED)
			self.Button4.configure(command=lambda: self.saveDetails(self.Listbox1.get(self.Listbox1.curselection())))

			#configure labels
			self.Label1 = Label(new)
			self.Label1.place(relx=0.483, rely=0.133, height=21, width=54)
			self.Label1.configure(justify='right')
			self.Label1.configure(text='''Title:''')

			self.Label2 = Label(new)
			self.Label2.place(relx=0.483, rely=0.267, height=21, width=54)
			self.Label2.configure(justify='right')
			self.Label2.configure(text='''IP:''')

			self.Label3 = Label(new)
			self.Label3.place(relx=0.483, rely=0.4, height=21, width=54)
			self.Label3.configure(justify='right')
			self.Label3.configure(text='''Port:''')

			self.Label4 = Label(new)
			self.Label4.place(relx=0.483, rely=0.533, height=21, width=54)
			self.Label4.configure(justify='right')
			self.Label4.configure(text='''Protocol:''')			

			#after window has been configured, populate listbox with streams read from streams.json
			Manage_Window.showList(self)

#######################################################################################################################################################################################################
#global functions
#many, if not all, of these functions could (**SHOULD**) be moved under the LAPCStream class with no effect to functionality

#function to return root object 
def Tk_get_root():
	if not hasattr(Tk_get_root, "root"):
		Tk_get_root.root = Tk()
	return Tk_get_root.root

#function to gracefully shut down on [x] or menubar 'Quit'
def _quit():
	root = Tk_get_root()
	root.quit()
	root.destroy()

#function to stop stream (while retaining media_player object) - it also updates the channel guide to indicate that no stream is currently playing
def end_stream(self):
	if self.player.is_playing() and self.currently_playing:
		self.player.stop()
		index = self.ListBox1.get(0,END).index(self.currently_playing + ' ▶')
		if self.ListBox1.get(index)[-2:] == " ▶":
			icontext = self.ListBox1.get(index)[:-2]
			self.ListBox1.delete(index)
			self.ListBox1.insert(index, icontext)
		self.currently_playing = ''
		toggleEndStreamButton(self)

#function to begin media_player object streaming - it also updates the channel guide to indicate which stream is currently playing 
def start_stream(self, netstream):
	end_stream(self)
	self.ListBox1.configure(exportselection=0)
	#media = self.Instance.media_new(netstream.mrl)
	self.player.set_mrl(netstream.mrl)
	self.player.play()
	self.setTitle(netstream.name)
	time.sleep(2)
	self.currently_playing = netstream.name
	if not self.player.is_playing():
		alert(netstream.name + ' stream could not be opened.')
		self.currently_playing = ''
	else:
		#play icon
		index = self.ListBox1.curselection()
		icontext = self.ListBox1.get(index) + " ▶"
		self.ListBox1.delete(index)
		self.ListBox1.insert(index, icontext)
		toggleEndStreamButton(self)

#this function populates the channel guide listbox with the stream objects parsed from streams.json
def populate_stream(self, netstream):
	self.ListBox1.insert(END, netstream.name)
	if netstream.name == self.currently_playing:
		#play icon
		index = self.ListBox1.get(0,END).index(self.currently_playing)
		icontext = self.ListBox1.get(index) + " ▶"
		self.ListBox1.delete(index)
		self.ListBox1.insert(index, icontext)

#this function grabs stream data from streams.json according to which stream is selected in the listbox and sends it to be played in start_stream
#this function, among others, would gain efficiency from saving streams.json data in memory for the lifecycle of the application 
def stream_select(self, name):
	storedStreams = getStored(self)
	tempStream = {}
	for i in storedStreams['streams']:
		if storedStreams['streams'][i]['title'] == name:
			tempStream = storedStreams['streams'][i]
			break
	tempMRL = buildMRL(tempStream['protocol'], tempStream['ip'], tempStream['port'])
	netstream = stream(name = tempStream['title'], mrl = tempMRL)
	start_stream(self, netstream)
	
#this function reads streams.json and returns contents in json form (dict)
def getStored(self):
	f = open('streams.json')
	jsonData = json.load(f)
	f.close()
	return jsonData

#this function constructs a stream mrl from ip, port, and protocol -- does not account for source-specific address
def buildMRL(protocol, ip, port=None):
	mrl = protocol + "://@" + ip + (':' + port if port else '')
	return mrl

#this function parses streams.json data into stream objects and sends them to be populated in populate_stream 
def populateStored(self):
	self.ListBox1.delete(0, END)
	jsonData = getStored(self)
	storedStreams = []
	for i in jsonData['streams']:
		tempMRL = buildMRL(jsonData['streams'][i]['protocol'], jsonData['streams'][i]['ip'], jsonData['streams'][i]['port'])
		tempStream = stream(name = jsonData['streams'][i]['title'], mrl = tempMRL)#, server = 'All Streams')
		storedStreams.append(tempStream)
	names = []
	for item in storedStreams:
		populate_stream(self, item)
		names.append(item.name)
	self.ListBox1.select_set(0)
	if self.currently_playing not in names:
		self.player.stop()
		self.currently_playing = ''
		toggleEndStreamButton(self)

#this function opens the manage window -- this definitely has no business being global scope
def open_manage(self):
	mw = Manage_Window(self)

#calls the tkinter showerror function (creates a window with an error dialog) populated with the msg argument
def alert(msg):
	showerror('Error', msg)

#ensures that a frame is centered on the screen -- rarely used??
def center(toplevel):
	screen_width = toplevel.winfo_screenwidth()
	screen_height = toplevel.winfo_screenheight()

	size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
	x = screen_width/2 - size[0]/2
	y = screen_height/2 - size[1]/2

	toplevel.geometry("+%d+%d" % (x,y))

#when a stream is ended for whatever reason, this function is called to toggle the state of the 'End Current Stream' button so that it is only active when a stream is currently playing
def toggleEndStreamButton(self):
	if not self.currently_playing:
		self.menubar.entryconfig("End Current Stream", state="disabled")
	else:
		self.menubar.entryconfig("End Current Stream", state="normal")

#calls the tkinter showinfo function (creates a window with an info dialog) populated with the global var about
def about(msg):
	showinfo('About', msg)

#######################################################################################################################################################################################################

