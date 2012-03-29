#!/usr/bin/env python
#
# Author: Nick DiRienzo
# Started on: 07.13.2011
#
# TODO: Structure the code better.

import os
import re
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.ext import db

class Post(db.Model):
    path = db.StringProperty()
    title = db.StringProperty()
    content = db.TextProperty()
    timestamp = db.DateTimeProperty(auto_now_add=True)

class Page(webapp.RequestHandler):
    def render(self, page_name, dir, template_vars={}):
        vars = {}
        path = os.path.join(os.path.dirname(__file__), "templates", page_name + ".html")
        user = users.get_current_user()
        if user:
            vars["username"] = user.nickname()
            vars["logout_url"] = users.create_logout_url(dir)
            vars["is_admin"] = users.is_current_user_admin()
        else:
            vars["username"] = None
            vars["login_url"] = users.create_login_url(dir)
        vars["page_name"] = page_name
        vars.update(template_vars)
        self.response.out.write(template.render(path, vars))

class StaticPageHandler(Page):
    def get(self, page_name):
        if page_name == "":
            self.render("home", "/")
        elif page_name == "projects":
            self.render("projects", "/projects")
        elif page_name == "talks":
            self.render("talks", "/talks")
        else:
            self.render("404", "/uh-oh")

class PostHandler(Page):
    def get(self, path):
        if path:
            post = BlogPost.all().filter("path = ", path).get()
            if post:
                self.render("blog_post", "/post/%s" % path, {"post": post})
            else:
                self.redirect("/404")
        else:
            self.render("posts", "/posts", {"posts": Post.all().order("-timestamp")})

def main():
    application = webapp.WSGIApplication(
                                        [("/posts/(.*)", PostHandler),
                                        ("/(.*)", StaticPageHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == "__main__":
    main()
