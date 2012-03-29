#!/usr/bin/env python
#
# Author: Nick DiRienzo
# Started on: 07.13.2011
#
# TODO: Structure the code better.

import os
import re
import markdown2
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.ext import db

class Post(db.Model):
    slug = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    markdown = db.TextProperty(required=True)
    html = db.TextProperty(required=True)
    published = db.BooleanProperty(default=False)
    timestamp = db.DateTimeProperty(auto_now_add=True)

class Page(webapp.RequestHandler):
    def render(self, page_name, slug="", template_vars={}):
        page_vars = {}
        path = os.path.join(os.path.dirname(__file__), "templates", page_name + ".html")
        if not slug:
            slug = page_name if page_name != "home" else ""
        user = users.get_current_user()
        if user:
            page_vars["username"] = user.nickname()
            page_vars["logout_url"] = users.create_logout_url(slug)
            page_vars["is_admin"] = users.is_current_user_admin()
        else:
            page_vars["username"] = None
            page_vars["login_url"] = users.create_login_url(slug)
        page_vars["page_name"] = page_name
        page_vars.update(template_vars)
        self.response.out.write(template.render(path, page_vars))

class PageHandler(Page):
    def get(self, page_name):
        if page_name == "":
            self.render("home")
        elif page_name == "projects":
            self.render("projects")
        elif page_name == "talks":
            self.render("talks")
        elif page_name == "posts":
            self.redirect("/posts/")
        else:
            self.render("oops")

class PostHandler(Page):
    def get(self, slug):
        if slug:
            post = Post.all().filter("slug = ", slug).get()
            if post:
                self.render("post", "/post/%s" % slug, {"post": post})
            else:
                self.redirect("/oops")
        else:
            self.render("posts", "/posts", {"posts": Post.all().order("-timestamp")})

class PostPublishHandler(webapp.RequestHandler):
    def post(self, slug):
        if users.is_current_user_admin():
            post = Post.all().filter("slug = ", slug).get()
            post.published = True
            post.put()
            self.redirect("/posts/")
        else:
            self.redirect("/")

class PostUnpublishHandler(webapp.RequestHandler):
    def post(self, slug):
        if users.is_current_user_admin():
            post = Post.all().filter("slug = ", slug).get()
            post.published = False
            post.put()
            self.redirect("/posts/")
        else:
            self.redirect("/")

class PostDeleteHandler(webapp.RequestHandler):
    def post(self, slug):
        if users.is_current_user_admin():
            db.delete(Post.all().filter("slug = ", slug).get())
            self.redirect("/posts/")
        else:
            self.redirect("/")

class PostEditorHandler(Page):
    def get(self, slug=""):
        if slug:
            post = Post.all().filter("slug = ", slug).get()
            if post:
                self.render("post_editor", "/posts/edit/%s" % slug, {"title": post.title, "markdown": post.markdown})
            else:
                self.render("post_editor")
        else:
            self.render("post_editor")

    def post(self, slug=""):
        def slugify(title):
            """ Not sure where I found this RegEx, but I am still working on learning it myself. """
            title = title.lower()
            return re.sub(re.compile(r"[^a-zA-Z0-9-]+"), "", re.sub(re.compile("\s"), "-", title))
        
        if users.is_current_user_admin():
            title = self.request.get("pt")
            markdown = self.request.get("c")
            html = markdown2.markdown(markdown)
            if slug:
                post = Post.all().filter("slug = ", slug).get()
                post.title = title
                post.markdown = markdown
                post.html = html
                post.slug = slugify(title)
                post.put()
            else:
                slug = slugify(title)
                post = Post(slug=slug, title=title, markdown=markdown, html=html)
                post.put()
            self.redirect("/posts/%s" % slug)
        else:
            self.redirect("/")

def main():
    application = webapp.WSGIApplication(
                                        [("/posts/delete/(.*)", PostDeleteHandler),
                                        ("/posts/unpublish/(.*)", PostUnpublishHandler),
                                        ("/posts/publish/(.*)", PostPublishHandler),
                                        ("/posts/edit/(.*)", PostEditorHandler),
                                        ("/posts/(.*)", PostHandler),
                                        ("/(.*)", PageHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == "__main__":
    main()
