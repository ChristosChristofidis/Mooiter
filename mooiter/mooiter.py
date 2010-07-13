#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Mooiter
# Copyright 2010 Christopher Massey
# See LICENCE for details.

import sys
import os
import re
import datetime
import string
import hashlib

#Test 3rd party modules
try:
    from PyQt4 import QtGui
    from PyQt4 import QtCore
    from PyQt4 import QtWebKit
    import tweepy
    import parser
    import keyring
    import account
except ImportError as e:
    print "Import Error" + e

class TwitterWindow(QtGui.QMainWindow):
    def __init__(self, Parent=None):
        super(TwitterWindow, self).__init__(Parent)

        #settings
        self.settings = QtCore.QSettings("cutiepie4", "Mooiter")

        self.resize(300, 550)
        self.setWindowTitle("Mooiter")

        #Menubar
        actionaccount = QtGui.QAction("&Account", self)
        self.connect(actionaccount, QtCore.SIGNAL('triggered()'), self.account_dialog)

        menubar = self.menuBar()
        menusettings = menubar.addMenu("&Settings")
        menusettings.addAction(actionaccount)
        

        self.tabmain = QtGui.QTabWidget()
        self.publicwid = QtGui.QWidget()

        self.publicvbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()

        #Create edit box and letter count into horizontal box
        self.label = QtGui.QLabel()
        self.label.setMinimumWidth(33)
        self.label.setText('140')
        self.intwit = TwitterEditBox(self)
        hbox.addWidget(self.intwit)
        hbox.addWidget(self.label)

        #Public Sub Tab Home
        self.subtab = QtGui.QTabWidget()
        self.subwidget = QtGui.QWidget()
        self.homevbox = QtGui.QVBoxLayout()

        self.view = QtWebKit.QWebView()
        self.view.page().mainFrame().setScrollBarPolicy\
                                     (QtCore.Qt.Horizontal, 
                                      QtCore.Qt.ScrollBarAlwaysOff)

        self.view.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)

        self.homevbox.addWidget(self.view)
        self.subwidget.setLayout(self.homevbox)
        self.subtab.addTab(self.subwidget, "Home")

        #Combine horizontal edit box to vertical box
        self.publicvbox.addLayout(hbox)

        
        self.publicvbox.addWidget(self.subtab)
        self.publicwid.setLayout(self.publicvbox)
        self.tabmain.addTab(self.publicwid, "Public")
        self.setCentralWidget(self.tabmain)
        self.intwit.setFocus()

        self.view.load(QtCore.QUrl(u'file://localhost%s' % os.path.abspath('.')))

        self.timeridle = QtCore.QTimer()
        self.timer = QtCore.QTimer()
        self.test_account()
            
        #Handle webview links
        self.connect(self.view, QtCore.SIGNAL("linkClicked(QUrl)"), self.open_link)

        #Count text length alterations
        self.connect(self.intwit, QtCore.SIGNAL("textChanged()"), self.twit_count)


        self.connect(self.intwit, QtCore.SIGNAL("status"), self.submit_twit)

    def account_dialog(self):
        dialog = account.TwitterAccount(self)
        self.connect(dialog, QtCore.SIGNAL("changed"), self.test_account)
        dialog.show()

    def test_account(self):
        """Load timeline if account exists"""

        self.timer.stop()
        if self.settings.contains("User"):
            username = self.settings.value("User").toString()
            password = keyring.get_password("Mooiter",
                                            hashlib.sha224(username).hexdigest())
            self.auth = tweepy.BasicAuthHandler(username, password)
            self.api = tweepy.API(self.auth)
            #Refresh twitter timeline every minute
            
            self.connect(self.timer, QtCore.SIGNAL("timeout()"), self.load_home_tweets)
            self.load_home_tweets()
            self.timer.start(300000)
        
    def open_link(self, url):
        """Determine url type"""

        result = url.toString().split(":")
        if result[0] == "hash":
            print "hash"
        elif result[0] == "user":
            user = result[1]
            tagwidget = TwitterTab(self, tag="user", text=user[2:], auth=self.api)
            self.subtab.addTab(tagwidget, user[2:])
        else:
            print result[0]
            QtGui.QDesktopServices.openUrl(url)
        
    def load_home_tweets(self):
        html = u'<html><head>\
                      <link rel="stylesheet" href="themes/theme_1/theme1.css"\
                        type="text/css" media="all" /></head><body>'
                      
        for twits in self.api.home_timeline():
            html += u'<div class="roundcorner_box">\
                      <div class="roundcorner_top"><div></div></div>\
                      <div class="roundcorner_content">'
            html += u'<div class="pic_left">'
            html += u'<img class="pic" src="' + twits.user.profile_image_url + u'" />'
            html += u'</div>'
            html += u'<div class="text_left">'
            html += u'<h2>' + twits.user.screen_name + u'</h2>'
            html += u'<p>' + parser.LinkParser().parse_links(twits.text) + u'</p>'
            html += u'<p>' + str(period_ago(twits.created_at)) + u'</p>'
            html += u'<p>via ' + twits.source + u'</p>'
            html += u'</div>'
            html += u'<div style="clear: both;"></div>'
            html += u'</div><div class="roundcorner_bottom"><div></div>\
                      </div></div><br />'

        html += u"</body></html>"
        self.view.setHtml(html, QtCore.QUrl(u'file://localhost%s' %\
                          os.path.abspath('./mooiter.py')))
        
    def twit_count(self):
        """Count the length of the tweet"""

        self.label.setText(str(140 - len(self.intwit.toPlainText())))

    def submit_twit(self):
        """Post twitter status to user account"""

        try:
            self.api.update_status(unicode(self.intwit.toPlainText()))
        except tweepy.TweepError:
            QtGui.QMessageBox.warning(self, 'Warning',
                                      "Error posting twitter status", 
                                      QtGui.QMessageBox.Ok)
        finally:
            self.intwit.setText("")

class TwitterEditBox(QtGui.QTextEdit):
    """Custom TextEdit Widget"""

    def __init__(self, Parent):
        super(TwitterEditBox, self).__init__(Parent)
        self.setMinimumHeight(50)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return:
            self.emit(QtCore.SIGNAL("status"))
        else:
            QtGui.QTextEdit.keyPressEvent(self, event)

#TODO
#Class Widget
class TwitterTab(QtGui.QWidget):
    """Create user or hash tag timeline.

    Args:
        tag: datetime object
        text: string username or hash tag
        auth: tweepy object

    """
    def __init__(self, Parent, tag, text, auth):
        super(TwitterTab, self).__init__(Parent)
        self.api = auth
        self.view = QtWebKit.QWebView()

        vbox = QtGui.QVBoxLayout()
        self.view.page().mainFrame().setScrollBarPolicy\
                                (QtCore.Qt.Horizontal, 
                                 QtCore.Qt.ScrollBarAlwaysOff)

        self.view.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
        
        vbox.addWidget(self.view)
        self.setLayout(vbox)
     
        if tag == "user":
            self.load_user_tweets(text)
        else:
            print "twitter tab"
            
    def load_user_tweets(self, text):
        html = u'<html><head>\
                      <link rel="stylesheet" href="themes/theme_1/theme1.css"\
                      type="text/css" media="all" /></head><body>'

        html += u'<div class="roundcorner_box">\
                  <div class="roundcorner_top"><div></div></div>\
                  <div class="roundcorner_content">'
        html += u'<h2>' + self.api.get_user(text).screen_name + u'</h2>'
        html += u'</div><div class="roundcorner_bottom"><div></div>\
                  </div></div><br />'

        for twits in self.api.user_timeline(text):
            html += u'<div class="roundcorner_box">\
                      <div class="roundcorner_top"><div></div></div>\
                      <div class="roundcorner_content">'
            html += u'<div class="pic_left">'
            html += u'<img class="pic" src="' + twits.user.profile_image_url + u'" />'
            html += u'</div>'
            html += u'<div class="text_left">'
            html += u'<h2>' + twits.user.screen_name + u'</h2>'
            html += u'<p>' + parser.LinkParser().parse_links(twits.text) + u'</p>'
            html += u'<p>' + str(period_ago(twits.created_at)) + u'</p>'
            html += u'<p>via ' + twits.source + u'</p>'
            html += u'</div>'
            html += u'<div style="clear: both;"></div>'
            html += u'</div><div class="roundcorner_bottom"><div></div>\
                      </div></div><br />'

        html += u"</body></html>"
        self.view.setHtml(html, QtCore.QUrl(u'file://localhost%s' %\
                          os.path.abspath('./mooiter.py')))

#class TwitterBar(QtGui.QTabBar):
#    super(TwitterBar, self).__init__(Parent)

#    def tabInserted(self, index):
#        pass

def period_ago(period):
    """Provides the time and date difference of a tweet.

    Args:
        period: datetime object

    Returns:
        Formatted time and date difference as a unicode string.
    """
        
    if not isinstance(period, datetime.datetime):

        return "error"
    #Determine time and date difference
    difference = datetime.datetime.utcnow() - period
    diff_day = string.split(str(difference))

    #More than 1 day old use full date and time
    if len(diff_day) > 1:
        return period.strftime("%c")
    else:
        diff_split = string.split(str(difference), ":")
        hour = int(diff_split[0])
        minute = int(diff_split[1])
        second = int(string.split(str(diff_split[2]), ".")[0])
        return_diff = ""

        #Format time while determining the plurals
        if hour > 0:
            if hour == 1:
                return_diff += u"(%s hour " % hour
            else:
                return_diff += u"(%s hours " % hour

            if minute == 1:
                return_diff += u"%s minute " % minute
            else:
                return_diff += u"%s minutes " % minute

            if second == 1:
                return_diff += u"%s second ago)" % second
            else:
                return_diff += u"%s seconds ago)" % second

        elif minute > 0:
            if minute == 1:
                return_diff += u"(%s minute " % minute
            else:
                return_diff += u"(%s minutes " % minute

            if second == 1:
                return_diff += u"%s second ago)" % second
            else:
                return_diff += u"%s seconds ago)" % second
                
        else:
            if second == 1:
                return_diff += u"(%s second ago)" % second
            else:
                return_diff += u"(%s seconds ago)" % second

        return return_diff        

if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    meep = TwitterWindow()
    meep.show()
    sys.exit(app.exec_())