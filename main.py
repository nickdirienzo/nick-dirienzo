#!/usr/bin/env python
#
# Author: Nick DiRienzo
# Started on: 07.13.2011
#
# TODO: Structure the code better.

import os
import math
import re
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.ext import db

class StaticPage(db.Model):
    page_name = db.StringProperty()
    page_content = db.TextProperty()

class Page(webapp.RequestHandler):
    def render(self, page_name, dir, template_vars={}):
        vars = {}
        path = os.path.join(os.path.dirname(__file__), "templates", page_name + ".html")
        user = users.get_current_user()
        if user:
            vars["username"] = user.nickname()
            vars["logout_url"] = users.create_logout_url(dir)
            if users.is_current_user_admin():
                vars["is_admin"] = True
            else:
                vars["is_admin"] = False
        else:
            vars["username"] = None
            vars["login_url"] = users.create_login_url(dir)
        vars["page_name"] = page_name
        #vars["content"] = StaticPage.all().filter("page_name = ", page_name)
        vars.update(template_vars)
        self.response.out.write(template.render(path, vars))

class AboutHandler(Page):
    def get(self):
        self.render("about", "/about")
        
class QuickRefsHandler(Page):
    def get(self):
        self.render("quick_refs", "/quick_references")
        
class HaskellRefHandler(Page):
    def get(self):
        self.render("haskell_ref", "/quick_references/haskell")
        
class ProjectsHandler(Page):
    def get(self):
        self.render("projects", "/projects")
        
class HomeHandler(Page):
    def get(self):
        self.render("home", "/", {"posts": BlogPost.all().order("-timestamp")})
    
class BlogHandler(Page):
    def get(self):
        tag = self.request.get("tag")
        post_path = self.request.get("title")
        page_num = self.request.get("page")
        posts_per_page = 10
        if page_num == "" or page_num == "0":
            page_num = 1
        else:
            page_num = int(page_num)
        self.render_posts(self.get_all_posts(), page_num, posts_per_page)
        
    def post(self):
        title_error = False
        title = self.request.get("post-title")
        content_error = False
        content = self.request.get("post-content")
        tags = self.request.get("post-tags").split(", ")
        if title != "" and BlogPost.all().filter("title = ", title).count() == 0 and content != "":
            post = BlogPost()
            post.path = self.create_path(title)
            post.title = title
            post.content = content
            post.put()
            self.generate_tags(tags, post)
            self.redirect("/blog")
        else:
            if BlogPost.all().filter("title = ", title).count() != 0:
                title_exists_error = True
            elif title == "":
                title_error = True
            if content == "":
                content_error = True
            self.redirect("/blog")
    
    def render_posts(self, query, curr_page, posts_per_page):
        post_count = query.count()
        num_pages = math.ceil(post_count/float(posts_per_page))
        if num_pages == 0:
            num_pages = 1
        self.render("blog", "/blog", {
            "posts": query.order("-timestamp").fetch(posts_per_page, (curr_page - 1) * posts_per_page), 
            "prev_page": curr_page - 1,
            "next_page": curr_page + 1,
            "on_last_page": (curr_page == num_pages),
            "first_page_is_last_page": post_count < posts_per_page,
            "post_exists": post_count > 0
        })
        
    def get_all_posts(self):
        return BlogPost.all()
            
    def create_path(self, title):
        ''' Creates a better path for posts. "Hello-World-Hello-University". '''
        pattern = re.compile("\s")
        temp_path = re.sub(pattern, "-", title)
        pattern = re.compile(r"[^a-zA-Z0-9-]+")
        return re.sub(pattern, "", temp_path)
        
    ''' Takes the list of tags, and strips whitespace and returns the words separated by hypens. '''
    def generate_tags(self, tag_list, post):
        for tag in tag_list:
            blog_tag = BlogPostTag(post=post, name=tag, path=self.create_path(tag)).put()   
    
class BlogPostHandler(Page):
    def get(self):
        """ Generates a page with a single blog post. Otherwise displays a 'Post Not Found' error. """
        path = self.request.path
        title = path.split("/")[len(path.split("/"))-1]
        post = BlogPost.all().filter("path = ", title).get()
        self.render("blog_post", "/blog/post/" + title, {"post": post, "post_exists": post != None})

class BlogTagHandler(Page):
    def get(self):
        path = self.request.path
        tag = path.split("/")[len(path.split("/"))-1]
        query = BlogPostTag.all().filter("path = ", tag)
        tag_models = query.order("-timestamp").fetch(query.count())
        # I don't like having to create two lists, there has to be a better way
        posts = []
        for model in tag_models:
            posts.append(model.post)
        self.render("posts_by_tag", "/blog/tag/" + tag,{"posts": posts, "tag": tag.replace("-", " "), "post_exists": query.count() > 0})
        

# I should make an AJAX way to do this...
class EditBlogPostHandler(Page):
    def get(self):
        query_post = BlogPost.all().filter("title = ", self.request.get("post-title")).get()
        self.render("blog_edit", "/blog/edit", {
            "title": query_post.title,
            "content": query_post.content,
            "tags": query_post.tags
        })

    def post(self):
        query_post = BlogPost.all().filter("title = ", self.request.get("title")).get()
        if query_post == None:
            self.redirect("/blog")
        else:
            updated_tags = self.request.get("updated-tags").split(", ")
            if query_post.title != "" and query_post.content != "":
                query_post.path = self.create_path(self.request.get("updated-title"))
                query_post.title = self.request.get("updated-title")
                query_post.content = self.request.get("updated-content")
                self.generate_tags(updated_tags, query_post)
                query_post.put()
                self.redirect("/blog")
            else:
                if BlogPost.all().filter("title = ", title).count() != 0:
                    title_exists_error = True
                elif title == "":
                    title_error = True
                if content == "":
                    content_error = True
                self.render("blog_edit", "/blog/edit", {
                    "title": query_post.title,
                    "content": query_post.content,
                    "tags": query_post.tags,
                    "title_exists_error": title_exists_error,
                    "title_error": title_error, 
                    "content_error": content_error
                })
                
    ''' Same as the generate_tags method in BlogHandler, except it deletes all tags and then regenerates them.
        I know it's not the right way to do this nor is it the efficient method. '''
    def generate_tags(self, tag_list, post):
        for tag in post.tags:
            tag.delete()
        for tag in tag_list:
            blog_tag = BlogPostTag()
            blog_tag.name = tag
            blog_tag.path = self.create_path(tag)
            blog_tag.post = post
            blog_tag.put()
    
    ''' Takes "This is a test" or "This...test" and returns "this-is-test" '''
    def create_path(self, title):
        pattern = re.compile("\s")
        temp_path = re.sub(pattern, "-", title)
        pattern = re.compile(r"[^a-zA-Z0-9-]+")
        return re.sub(pattern, "", temp_path)
        
class BlogPost(db.Model):
    path = db.StringProperty()
    title = db.StringProperty()
    content = db.TextProperty()
    timestamp = db.DateTimeProperty(auto_now_add=True)
    
class BlogPostTag(db.Model):
    post = db.ReferenceProperty(BlogPost, collection_name="tags")
    name = db.StringProperty() # e.g. Blog Development
    path = db.StringProperty() # e.g. Blog-Development
    timestamp = db.DateTimeProperty(auto_now_add=True)
    
class BlogCommentAuthor(db.Model):
    name = db.StringProperty()
    account = db.UserProperty(auto_current_user=True)
    use_name = db.BooleanProperty(default=False)
    
class BlogPostComment(db.Model):
    post = db.ReferenceProperty(BlogPost, collection_name="comments")
    author = db.ReferenceProperty(BlogCommentAuthor)
    content = db.TextProperty()
    timestamp = db.DateTimeProperty(auto_now_add=True)
    
class BlogCommentHandler(webapp.RequestHandler):
    def post(self):
        title = self.request.get("post")
        post = BlogPost.all().filter("path = ", title).get()
        comment = self.request.get("comment-content")
        no_comment = False
        name = self.request.get("comment-name")
        if comment == "":
            pass
        else:
            author = BlogCommentAuthor()
            if name != "":
                author.name = name
                author.use_name = True
            author.put()
            post_comment = BlogPostComment()
            post_comment.author = author
            post_comment.post = post
            post_comment.content = comment
            post_comment.put()
            mail.send_mail_to_admins(
                "Site Robot <bot@nickdirienzo.com>",
                "New Comment For Post: " + title,
                "Author: " + (author.name if author.use_name else author.account) + 
                "\nposted a comment on post titled " + title + "\n\nComment:\n" + comment
            )
        self.redirect("/blog/post/" + title)
        
class DeleteBlogCommentHandler(webapp.RequestHandler):
    def get(self):
        path = self.request.path
        key = path.split("/")[len(path.split("/"))-1]
        comment = BlogPostComment.get(key)
        comment.delete()
        self.redirect("/blog/post/" + self.request.get("post"))

class NoteCardsHandler(Page):
    def get(self):
        self.render("note_cards", "/note_cards", {"cards": db.GqlQuery("SELECT * FROM Card ORDER BY timestamp DESC")})
        
    def post(self):
        content = self.request.get("card-content")
        title = self.request.get("card-name")
        if content != "" and title != "":
            if Card.all().filter("title = ", title).count() == 1:
                card = Card.all().filter("title = ", title).get()
            else:
                card = Card()
                card.title = title
            card.put()
            note = CardNote(card_ref = card, content = content)
            note.put()
            self.redirect("/note_cards")
        self.render("note_cards", "/note_cards", {"cards": db.GqlQuery("SELECT * FROM Card ORDER BY timestamp DESC"), "no_input": True})

class EditNoteHandler(webapp.RequestHandler):
    def post(self):
        note_id = self.request.get("note_id")
        note = CardNote.get(note_id)
        

""" A card holds notes, and notes are oganized by card title. """
class Card(db.Model):
    title = db.StringProperty()
    timestamp = db.DateTimeProperty(auto_now_add=True)
    
""" And these are the notes that a card holds. """
class CardNote(db.Model):
    card_ref = db.ReferenceProperty(Card, collection_name="notes")
    content = db.StringProperty()

class NotFoundHandler(Page):
    def get(self):
        self.error(404)
        self.render("404", "/404", {})

def main():
    application = webapp.WSGIApplication(
                                        [("/", HomeHandler),
                                        ("/about", AboutHandler), 
                                        ("/projects", ProjectsHandler),
                                        ("/note_cards", NoteCardsHandler),
                                        ("/blog", BlogHandler),
                                        ("/blog/post/.*", BlogPostHandler),
                                        ("/blog/tag/.*", BlogTagHandler),
                                        ("/blog/edit", EditBlogPostHandler),
                                        ("/blog/comment", BlogCommentHandler),
                                        ("/blog/comment/delete/.*", DeleteBlogCommentHandler),
                                        ("/quick_references", QuickRefsHandler),
                                        ("/quick_references/haskell", HaskellRefHandler),
                                        ("/.*", NotFoundHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == "__main__":
    main()
