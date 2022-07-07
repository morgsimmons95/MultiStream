import LAPCStream

if __name__ == "__main__":

	#LAPCS instantiation
	root = LAPCStream.Tk_get_root()
	root.protocol("WM_DELETE_WINDOW", LAPCStream._quit)
	player = LAPCStream.LAPCStream(root, '')

	#mainloop
	root.mainloop()