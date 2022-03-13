import base64
import os
import requests
import threading

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import strip_tags
from django.core.files.base import ContentFile
from meta.views import Meta

from website.models import *


# Definition of functions:

def get_website_section(requested_website_position_id):
    """
    Fetch WebsiteSection with website_position_id

    Parameters

    ----------
    requested_website_position_id: string

    Return
    ------
    returns WebsiteSection object or None if not found
    """
    try:
        section = WebsiteSection.objects.get(
            website_position_id=requested_website_position_id)
    except ObjectDoesNotExist:
        section = None
    return section


def get_latest_news_posts(limit):
    """
    Fetch Latest NewsPosts according to post_date

    Parameters
    ----------
    limit : int

    Return
    ------
    returns a list of NewsPost objects
    """
    return NewsPost.objects.order_by('-post_date')[0:limit]


def has_commit_permission(access_token, repository_name):
    """
    Determine if user has commit access to the repository in dipy organisation.

    Parameters
    ----------
    access_token : string
        GitHub access token of user.
    repository_name : string
        Name of repository to check if user has commit access to it.
    """
    if access_token == '':
        return False
    headers = {'Authorization': 'token {0}'.format(access_token)}
    response = requests.get('https://api.github.com/orgs/dipy/repos',
                            headers=headers)
    response_json = response.json()
    for repo in response_json:
        if repo["name"] == repository_name:
            permissions = repo["permissions"]
            if(permissions["admin"] and
               permissions["push"] and
               permissions["pull"]):
                return True
    return False


def get_facebook_page_feed(page_id, count):
    """
    Fetch the feed of posts published by this page, or by others on this page.

    Parameters
    ----------
    page_id : string
        The ID of the page.
    count : int
        Maximum number of posts to fetch.
    """
    app_id = settings.FACEBOOK_APP_ID
    app_secret = settings.FACEBOOK_APP_SECRET

    params = (page_id, count, app_id, app_secret)
    url = ("https://graph.facebook.com/%s/feed?limit=%s&access_token=%s|%s" %
           params)
    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError:
        return {}
    response_json = response.json()
    if 'data' in response_json:
        return response_json["data"]
    else:
        return {}


def get_twitter_bearer_token():
    """
    Fetch the bearer token from twitter and save it to TWITER_TOKEN
    environment variable
    """
    consumer_key = settings.TWITTER_CONSUMER_KEY
    consumer_secret = settings.TWITTER_CONSUMER_SECRET

    bearer_token_credentials = "%s:%s" % (consumer_key, consumer_secret)

    encoded_credentials = base64.b64encode(
        str.encode(bearer_token_credentials)).decode()
    auth_header = "Basic %s" % (encoded_credentials,)

    headers = {'Authorization': auth_header,
               'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}
    try:
        response = requests.post('https://api.twitter.com/oauth2/token',
                                 headers=headers,
                                 data={'grant_type': 'client_credentials'})
        response_json = response.json()
    except requests.exceptions.ConnectionError:
        response_json = {}
    if 'access_token' in response_json:
        token = response_json['access_token']
    else:
        token = ''
    os.environ["TWITER_TOKEN"] = token
    return token


def get_twitter_feed(screen_name, count):
    """
    Fetch the most recent Tweets posted by the user indicated
    by the screen_name

    Parameters
    ----------
    screen_name : string
        The screen name of the user for whom to return Tweets for.

    count : int
        Maximum number of Tweets to fetch.
    """
    try:
        token = os.environ["TWITER_TOKEN"]
    except KeyError:
        token = get_twitter_bearer_token()
    parms = (screen_name, str(count))
    url = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name=%s&count=%s" % parms
    headers = {'Authorization': 'Bearer %s' % (token,)}
    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError:
        return {}
    response_json = response.json()
    return response_json


def get_last_release():
    """
    Fetch latest Release number

    """
    # test if databases is empty
    if not DocumentationLink.objects.all():
        return []

    doc = DocumentationLink.objects.filter(displayed=True).exclude(version__contains='dev').order_by('-version')
    return doc[0].version if len(doc) else '0.0.0'


def update_documentations():
    """
    Check list of documentations from gh-pages branches of the dipy_web
    repository and update the database (DocumentationLink model).

    To change the url of the repository in which the documentations will be
    hosted change the DOCUMENTATION_REPO_OWNER and DOCUMENTATION_REPO_NAME
    in settings.py
    """
    url = "https://api.github.com/repos/%s/%s/contents/?ref=gh-pages" % (
        settings.DOCUMENTATION_REPO_OWNER, settings.DOCUMENTATION_REPO_NAME)
    base_url = "https://raw.githubusercontent.com/%s/%s/gh-pages/" % (
        settings.DOCUMENTATION_REPO_OWNER, settings.DOCUMENTATION_REPO_NAME)
    response = requests.get(url)
    response_json = response.json()
    all_versions_in_github = []

    # add new docs to database
    for content in response_json:
        if content["type"] == "dir":
            version_name = content["name"]
            all_versions_in_github.append(version_name)
            page_url = base_url + version_name
            try:
                DocumentationLink.objects.get(version=version_name)
            except ObjectDoesNotExist:
                d = DocumentationLink(version=version_name,
                                      url=page_url)
                d.save()
    all_doc_links = DocumentationLink.objects.all()

   # remove deleted docs from database
    for doc in all_doc_links:
        if doc.version not in all_versions_in_github:
            doc.delete()
        doc.is_updated = False
        doc.save()

    displayed_doc = DocumentationLink.objects.filter(displayed=True)
    displayed_id = [doc.id for doc in displayed_doc]
    # print(displayed_id)

    t = threading.Thread(target=update_doc_informations,
                         args=[displayed_id],
                         daemon=True)
    t.start()
    return {'ids': '_'.join(map(str, displayed_id))}


def update_doc_informations(ids):
    for doc in DocumentationLink.objects.filter(id__in=ids):
        print("UPDATE TUTORIALS")
        doc.tutorials = get_doc_examples(doc.version)
        doc.save()
        print("UPDATE GALLERY")
        doc.gallery = get_doc_examples_images(doc.version)
        doc.save()
        print("UPDATE INTRO")
        doc.intro = get_dipy_intro(doc.version)
        doc.is_updated = True
        doc.save()
        print("updating ", doc.version)
    print("update Done")


def get_meta_tags_dict(title=settings.DEFAULT_TITLE,
                       description=settings.DEFAULT_DESCRIPTION,
                       keywords=settings.DEFAULT_KEYWORDS,
                       url="/", image=settings.DEFAULT_LOGO_URL,
                       object_type="website"):
    """
    Get meta data dictionary for a page

    Parameters
    ----------
    title : string
        The title of the page used in og:title, twitter:title, <title> tag etc.
    description : string
        Description used in description meta tag as well as the
        og:description and twitter:description property.
    keywords : list
        List of keywords related to the page
    url : string
        Full or partial url of the page
    image : string
        Full or partial url of an image
    object_type : string
        Used for the og:type property.
    """
    meta = Meta(title=title,
                description=description,
                keywords=keywords + settings.DEFAULT_KEYWORDS,
                url=url,
                image=image,
                object_type=object_type,
                use_og=True, use_twitter=True, use_facebook=True,
                use_title_tag=True)
    return meta


def get_youtube_videos(channel_id, count):
    """
    Fetch the list of videos posted in a youtube channel

    Parameters
    ----------
    channel_id : string
        Channel ID of the youtube channel for which the videos will
        be retrieved.

    count : int
        Maximum number of videos to fetch.
    """
    if not settings.GOOGLE_API_KEY:
        # Todo: logger, add warning
        return {}

    parms = (channel_id, settings.GOOGLE_API_KEY)
    url = "https://www.googleapis.com/youtube/v3/search?order=date&part=snippet&channelId=%s&maxResults=25&key=%s" \
          % parms
    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError:
        print('connection Error')
        return {}
    except Exception as e:
        print(e)
        return {}
    response_json = response.json()
    if 'error' in response_json.keys():
        print(response_json)
        return {}

    videos = [items for items in response_json['items']
              if items['id']['kind'] == "youtube#video"]
    return videos


def get_docs(version=None):
    """Returns documentation object"""
    if version is None:
        doc = DocumentationLink.objects.filter(displayed=True).exclude(version__contains='dev').order_by('-version')
    else:
        doc = DocumentationLink.objects.filter(version=version)

    if not doc:
        doc = DocumentationLink.objects.filter(displayed=True).order_by('-version')
    if not doc:
        print("Documentation not found")
        return []

    return doc


def get_dipy_intro(version=None):
    """Fetch Introduction information."""
    if not DocumentationLink.objects.all():
        return ['', '', '']

    doc = get_docs(version)
    version = doc[0].version
    path = 'index'
    repo_info = (settings.DOCUMENTATION_REPO_OWNER,
                 settings.DOCUMENTATION_REPO_NAME)
    base_url = "https://raw.githubusercontent.com/%s/%s/gh-pages/" % repo_info
    url = base_url + version + "/" + path + ".fjson"
    response = requests.get(url)
    if response.status_code == 404:
        url = base_url + version + "/" + path + "/index.fjson"
        response = requests.get(url)
        if response.status_code == 404:
            return []
    url_dir = url
    if url_dir[-1] != "/":
        url_dir += "/"

    # parse the content to json
    response_json = response.json()
    bs_doc = BeautifulSoup(response_json['body'], "lxml")

    examples_div = bs_doc.find("div", id="diffusion-imaging-in-python")
    intro_text_p = examples_div.find("p")
    intro_text_p.attrs['class'] = 'text-center'
    highlight_div = examples_div.find("div", id="highlights")
    highlight_div.h2.decompose()
    for link in highlight_div.find_all('a'):
        l =  link.get('href')
        if l.lower().startswith('#') or 'http:/' in l or 'https:/' in l:
            continue
        link['href'] = 'documentation/latest/{}'.format(l)

    annoucement = examples_div.find("div", id="announcements")
    annoucement.h2.decompose()
    for link in annoucement.find_all('a'):
        l = link.get('href')
        if l.lower().startswith('#') or 'http:/' in l.lower() or 'https:/' in l.lower():
            continue
        link['href'] = 'documentation/latest/{}'.format(l)
    for link in annoucement.find_all('img'):
        l = link.get('src')
        if 'http:/' in l.lower() or 'https:/' in l.lower():
            continue
        link['src'] = base_url + version + "/" + l

    return [str(intro_text_p), str(annoucement), str(highlight_div)]


def get_dipy_publications(count=3):
    """
        Fetch Publication information

    Parameters
    -----------
    count: int, optional
        maximal number of publications to fetch

        """
    if not DocumentationLink.objects.all():
        return []

    doc = get_docs()
    version = doc[0].version
    path = 'cite'
    repo_info = (settings.DOCUMENTATION_REPO_OWNER,
                 settings.DOCUMENTATION_REPO_NAME)
    base_url = "https://raw.githubusercontent.com/%s/%s/gh-pages/" % repo_info
    url = base_url + version + "/" + path + ".fjson"
    response = requests.get(url)
    if response.status_code == 404:
        url = base_url + version + "/" + path + "/index.fjson"
        response = requests.get(url)
        if response.status_code == 404:
            return []
    url_dir = url
    if url_dir[-1] != "/":
        url_dir += "/"

    # parse the content to json
    response_json = response.json()
    bs_doc = BeautifulSoup(response_json['body'], "lxml")
    publication_div = bs_doc.find("div", id="publications")
    publication_div.h1.decompose()
    publication = publication_div.find_all('p')
    if publication:
        publication = publication[:count]
    return ''.join([str(p) for p in publication])


def get_examples_list_from_li_tags(base_url, version, path, li_tags):
    """
    Fetch example title, description and images from a list of li tags
    containing links to the examples
    """

    examples_list = []
    url_dir = base_url + version + "/" + path + ".fjson/"

    for li in li_tags:
        link = li.find("a")
        if link and link.get('href').startswith('../examples_built'):
            # get images
            rel_url = "/".join(link.get('href')[3:].split("/")[:-1])
            example_url = base_url + version + "/" + rel_url + ".fjson"
            example_response = requests.get(example_url)
            example_json = example_response.json()
            example_title = strip_tags(example_json['title'])

            # replace relative image links with absolute links
            example_json['body'] = example_json['body'].replace(
                "src=\"../", "src=\"" + url_dir)

            # extract title and all images
            example_bs_doc = BeautifulSoup(example_json['body'], "lxml")
            example_dict = {"title": example_title,
                            "link": "/documentation/" + version + "/" + path + "/" + link.get('href'),
                            "description": example_bs_doc.p.text,
                            "images": []}
            for tag in list(example_bs_doc.find_all('img')):
                example_dict["images"].append(str(tag))
            examples_list.append(example_dict)

    return examples_list


def get_doc_examples(version=None):
    """
    Fetch all examples (tutorials) in latest documentation

    """
    # test if databases is empty
    import time
    start = time.time()
    if not DocumentationLink.objects.all():
        return []

    doc_examples = []
    doc = get_docs(version)
    version = doc[0].version
    path = 'examples_index'
    repo_info = (settings.DOCUMENTATION_REPO_OWNER,
                 settings.DOCUMENTATION_REPO_NAME)
    base_url = "https://raw.githubusercontent.com/%s/%s/gh-pages/" % repo_info
    url = base_url + version + "/" + path + ".fjson"
    response = requests.get(url)
    if response.status_code == 404:
        url = base_url + version + "/" + path + "/index.fjson"
        response = requests.get(url)
        if response.status_code == 404:
            return []
    url_dir = url
    if url_dir[-1] != "/":
        url_dir += "/"

    # parse the content to json
    response_json = response.json()
    response_json['body'] = response_json['body'].replace("¶", "")
    bs_doc = BeautifulSoup(response_json['body'], "lxml")

    examples_div = bs_doc.find("div", id="examples")
    # TOTOTOTOTOTOTOTOTOTOTOTOTOTOTOT
    # import ipdb; ipdb.set_trace()
    all_major_sections = examples_div.find_all("div",
                                               class_="section",
                                               recursive=False)
    print('DURATION {}s'.format(time.time() - start))
    start = time.time()
    for major_section in all_major_sections:
        major_section_dict = {}
        major_section_title = major_section.find("h2")
        major_section_dict["title"] = str(major_section_title)
        major_section_dict["minor_sections"] = []
        major_section_dict["examples_list"] = []
        major_section_dict["valid"] = True
        all_minor_sections = major_section.find_all("div",
                                                    class_="section",
                                                    recursive=False)

        if len(all_minor_sections) == 0:
            # no minor sections, only examples_list
            all_li = major_section.find("ul").find_all("li")
            major_section_dict[
                "examples_list"] = get_examples_list_from_li_tags(base_url,
                                                                  version,
                                                                  path,
                                                                  all_li)
            # check if there is no tutorial in major section:
            if len(major_section_dict["examples_list"]) == 0:
                major_section_dict["valid"] = False
        else:
            for minor_section in all_minor_sections:
                minor_section_dict = {}
                minor_section_title = minor_section.find("h3")
                minor_section_dict["title"] = str(minor_section_title)
                minor_section_dict["examples_list"] = []
                minor_section_dict["valid"] = True

                all_li = minor_section.find("ul").find_all("li")
                minor_section_dict[
                    "examples_list"] = get_examples_list_from_li_tags(base_url,
                                                                      version,
                                                                      path,
                                                                      all_li)
                # check if there is no tutorial in minor section:
                if len(minor_section_dict["examples_list"]) == 0:
                    minor_section_dict["valid"] = False
                major_section_dict["minor_sections"].append(minor_section_dict)
        doc_examples.append(major_section_dict)
    print('DURATION {}s'.format(time.time() - start))
    return doc_examples


def get_doc_examples_images(version=None):
    """
    Fetch all images in all examples in latest documentation

    """
    if not DocumentationLink.objects.all():
        return []

    doc = get_docs(version)
    version = doc[0].version
    path = 'examples_index'
    repo_info = (settings.DOCUMENTATION_REPO_OWNER,
                 settings.DOCUMENTATION_REPO_NAME)
    base_url = "https://raw.githubusercontent.com/%s/%s/gh-pages/" % repo_info
    url = base_url + version + "/" + path + ".fjson"
    response = requests.get(url)
    if response.status_code == 404:
        url = base_url + version + "/" + path + "/index.fjson"
        response = requests.get(url)
        if response.status_code == 404:
            return []
    url_dir = url
    if url_dir[-1] != "/":
        url_dir += "/"

    # parse the content to json
    response_json = response.json()
    bs_doc = BeautifulSoup(response_json['body'], 'html.parser')
    all_links = bs_doc.find_all('a')

    examples_list = []
    for link in all_links:
        if link.get('href').startswith('../examples_built'):
            rel_url = "/".join(link.get('href')[3:].split("/")[:-1])
            example_url = base_url + version + "/" + rel_url + ".fjson"
            example_response = requests.get(example_url)
            example_json = example_response.json()
            example_title = strip_tags(example_json['title'])

            # replace relative image links with absolute links
            example_json['body'] = example_json['body'].replace(
                "src=\"../", "src=\"" + url_dir)

            # extract title and all images
            example_bs_doc = BeautifulSoup(example_json['body'], 'html.parser')
            example_dict = {'title': example_title}
            link_href = link.get('href').split("#")[0]
            example_dict['link'] = '/documentation/' + version + "/" + path + "/" + link_href
            example_dict['description'] = example_bs_doc.p.text
            example_dict['images'] = []
            for tag in list(example_bs_doc.find_all('img')):
                example_dict['images'].append(str(tag))
            examples_list.append(example_dict)
    return examples_list


def save_profile_picture(strategy, user, response, details,
                         is_new=False,*args,**kwargs):

    backend = kwargs.get('backend', '')

    if backend and backend.name.lower() == 'github':
        avatar_url = response.get('avatar_url', '')
        first_name = details.get('first_name', '')
        last_name = details.get('last_name', '')

        if avatar_url:
            user.profile.avatar.save("{}.png".format(user.username), ContentFile(requests.get(avatar_url).content))
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.profile.save()
