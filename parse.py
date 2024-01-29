""" 
Github: JohnnySn0w
Convert data to markdown files

1 pages per solo message
1 page per conversation 
blog entries in md
this will make making pages a lot more simple
videos generally work in browser
"""

"""
an instruction will pin a tweet or display a bunch of tweets
an entry will hold the timeline cursor, or it will hold a tweet convo set or single tweet

the tricky thing ab entries:
if its a convo vs if it's a single tweet, they will have different paths?
there's a split: at .content, there will be a key 'items' if its a convo, or 
it will go straight to itemContent if solo tweet(each index of the 'items' array 
has item.itemContent prior). 
Also sometimes there wil be an extra 'tweet' key(menitioned in dict_chains.py)
"""
# builtin packages
import json
import os
import sys
import multiprocessing
import time

from datetime import datetime
from typing import Any, List, Optional, Set, Tuple, Union

# local files
from config import *
from dict_chains import *
from styling import *

"""
TODO: cleanup the two gens, clean up comments, link pfp to user profile on x
"""


def process_datetime(datetime_string: str, human_readable: bool = False) -> str:
    """
    Process the datetime string to create both a filename-friendly version
    and a human-readable version.

    Args:
        datetime_string (str): A string containing the datetime in the
                               format "Thu Oct 20 17:53:41 +0000 2022".
        human_readable (bool): Toggle output path. Default is False.

    Returns:
        str: Depending on args, either the filename-friendly datetime string
             or the human-readable datetime string.
    """
    # Parse the original datetime string
    datetime_obj = datetime.strptime(datetime_string, "%a %b %d %H:%M:%S +0000 %Y")

    if human_readable:
        return datetime_obj.strftime("%B %d, %Y, %I:%M:%S %p").replace(" 0", " ")
    else:
        return datetime_obj.strftime("%Y-%m-%d_%H-%M-%S")


def get_nested_value(obj: Union[dict, list], keys: List[Union[str, int]]) -> Any:
    """
    Make sure all sequential keys exist so we don't make an oopsy.

    Args:
        obj (Union[dict, list]): A JSON object or a list.
        keys (List[Union[str, int]]): An array of the key/index sequence we want to dig into.

    Returns:
        Any: The value of the last key/index or None if any key/index is not found.
    """
    for key in keys:
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        elif isinstance(obj, list) and isinstance(key, int) and key < len(obj):
            obj = obj[key]
        else:
            return None
    return obj  # which is actually now the value at the bottom of the key/index stack


def get_text(
    json_object: dict,
    instruction_index: int,
    entry_index: int,
    item_index: Optional[int] = None,
) -> Optional[str]:
    """
    Get text from item.

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.
        entry_index (int): Index for the current entry.
        item_index (Optional[int]): Optional index to locate the item.

    Returns:
        Optional[str]: Tweet text from a conversation, or None if the path is not found.
    """
    text = get_nested_value(
        json_object, tweet_chain(instruction_index, entry_index, item_index)
    )
    if text is None:
        text = get_nested_value(
            json_object,
            tweet_chain(instruction_index, entry_index, item_index, alt=True),
        )
        if text is None:
            return None
    # This replace fixes a newline issue(tweets can have those!), make sure pelican or whatever gen you're using has the md extension nl2br enabled
    return text.replace("\n\n", "\n> ")


def get_media_urls(
    json_object: dict,
    instruction_index: int,
    entry_index: int,
    item_index: Optional[int] = None,
) -> Optional[List[Tuple[str, str, str]]]:
    """
    Generate all of the best media URLs attached to an item.

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.
        entry_index (int): Index for the current entry.
        item_index (Optional[int]): Optional index to locate the item.

    Returns:
        Optional[List[Tuple[str, str, str]]]: A list of tuples containing media URLs, or None.
    """
    media = get_nested_value(
        json_object, media_chain(instruction_index, entry_index, item_index)
    )

    if media is None:
        media = get_nested_value(
            json_object,
            media_chain(instruction_index, entry_index, item_index, alt=True),
        )

    if media is not None:
        for thing in media:
            variant_index = None
            media_type = get_nested_value(thing, media_type_chain)
            if media_type == "video" or media_type == "animated_gif":
                bitrate = -1
                for variation_index, variation in enumerate(
                    get_nested_value(thing, media_variants_chain)
                ):
                    if (
                        variation["content_type"] == "video/mp4"
                        and variation["bitrate"] > bitrate
                    ):
                        # grab the highest bitrate url
                        bitrate = variation["bitrate"]
                        variant_index = variation_index
        return [
            (
                get_nested_value(thing, media_url_chain(variant_index)),
                get_nested_value(thing, media_url_direct_chain),
                get_nested_value(thing, media_type_chain),
            )
            for thing in media
        ]
    else:
        return None


# handle is the @
def get_user_info(
    json_object: dict,
    instruction_index: int,
    entry_index: int,
    item_index: Optional[int] = None,
) -> Optional[Tuple[str, str, str]]:
    """
    Get the user profile picture URL, handle, and name.

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.
        entry_index (int): Index for the current entry.
        item_index (Optional[int]): Optional index to locate the item.

    Returns:
        Optional[Tuple[str, str, str]]: A tuple of user profile picture URL, user handle, and user name from a conversation, or None if not found.
    """
    user_pfp, user_handle, user_name = (
        get_nested_value(json_object, chain)
        for chain in user_chain(instruction_index, entry_index, item_index)
    )

    if not all([user_pfp, user_handle, user_name]):
        user_pfp, user_handle, user_name = (
            get_nested_value(json_object, chain)
            for chain in user_chain(
                instruction_index, entry_index, item_index, alt=True
            )
        )
        if not all([user_pfp, user_handle, user_name]):
            return None
    return (user_pfp, user_handle, user_name)


def get_datetime(
    json_object: dict,
    instruction_index: int,
    entry_index: int,
    item_index: Optional[int] = None,
) -> Optional[str]:
    """
    Get the datetime of the item.

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.
        entry_index (int): Index for the current entry.
        item_index (Optional[int]): Optional index to locate the item.

    Returns:
        Optional[str]: String with the datetime (which is how its formatted in the json), or None if not found.
    """
    date_time = get_nested_value(
        json_object, datetime_chain(instruction_index, entry_index, item_index)
    )
    if date_time is None:
        # this will occur rarely, but sometimes an extra key is added in the list, so the chain needs to change
        date_time = get_nested_value(
            json_object,
            datetime_chain(instruction_index, entry_index, item_index, alt=True),
        )
        if date_time is None:
            return None
    return date_time


def get_valid_entries(
    json_object: dict, instruction_index: int
) -> List[Tuple[int, str]]:
    """
    Get the valid entry indices for tweets instead of unwanted data.

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.

    Returns:
        List[Tuple[int, str]]: A list of valid entry indices for conversations and tweets, with their type.
    """
    # Function body remains the same

    entries = get_nested_value(json_object, entry_chain(instruction_index))
    if entries is None:
        return []
    entry_list = []
    for entry_index, entry in enumerate(entries):  # unchanged
        if invalid_entryid_type not in get_nested_value(
            entries, entryid_chain(entry_index)
        ):
            entry_list.append(
                (entry_index, get_nested_value(entry, entry_type_name_chain))
            )
    return entry_list


def get_valid_instructions(json_object: dict) -> List[int]:
    """
    Even higher level than the entries, this is where pinned tweets are separated out.

    Args:
        json_object (dict): The line being worked with.

    Returns:
        List[int]: An array of valid indices.
    """
    instructions = get_nested_value(json_object, instruction_chain)
    return [
        instruction_index
        for instruction_index, _ in enumerate(instructions)
        if get_nested_value(instructions, instruction_type_chain(instruction_index))
        == valid_instruction_type
    ]


def get_items(json_object: dict, instruction_index: int, entry_index: int) -> List[int]:
    """
    Dig down to item set for the current entry.

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.
        entry_index (int): Index for the current entry.

    Returns:
        List[int]: A list of valid item indexes.
    """
    items = get_nested_value(json_object, item_chain(instruction_index, entry_index))
    if items is None:
        return [None]
    return [item_index for item_index, _ in enumerate(items)]


def gen_media_body(
    json_object: dict,
    instruction_index: int,
    entry_index: int,
    tags: set,
    item_index: Optional[int] = None,
) -> List[str]:
    """
    Generate media body, if media is present

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.
        entry_index (int): Index for the current entry.
        tags (set): holds tags for media categorizing
        item_index (int): May be None, used to switch between different body types

    Returns:
        List holding html items for main tweet bodies
    """
    media_urls = get_media_urls(json_object, instruction_index, entry_index, item_index)
    media_body = []
    if media_urls is not None:
        if len(media_urls) > 1:
            tags.add("photos")
        for _, media_info in enumerate(media_urls):
            media_url, media_url_direct, media_type = media_info
            tags.add(media_type)
            if media_type == "video":
                media_embed = f'<video width="100%" height="auto" controls><source src="{media_url}" type="video/mp4"/>Your browser does not support the video tag.</video>'
            elif media_type == "animated_gif":
                media_embed = f'<video width="100%" height="auto" autoplay loop muted><source src="{media_url}" type="video/mp4"/>Your browser does not support the video tag.</video>'
            else:
                media_embed = f'<img src="{media_url}" width="100%" height="auto" />'
            media_body.append(
                f'> <a href="{media_url}" target="_blank">{media_embed}</a>\n\n'
            )
        if media_body:
            media_body.append(f"[source tweet]({media_url_direct})\n\n")
    return media_body


def gen_main_body(
    json_object: dict,
    instruction_index: int,
    entry_index: int,
    authors: Set[str],
    item_index: Optional[int] = None,
) -> Tuple[str, Optional[int]]:
    """
    Generate main tweet/profile body

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.
        entry_index (int): Index for the current entry.
        authors (set): holds tagged authors
        item_index (int): May be None, used to switch between different body types

    Returns:
        Tuple containing the body for a tweet's media, plus the item_index it corresponds to if there are multiple items

    Raises:
        TypeError: If an error occurs in parsing the entry.
    """
    try:
        user_pfp, user_handle, user_name = get_user_info(
            json_object, instruction_index, entry_index, item_index
        )
        date_time = get_datetime(
            json_object, instruction_index, entry_index, item_index
        )
        tweet = get_text(json_object, instruction_index, entry_index, item_index)
        authors.add(user_handle)
        if not all([user_pfp, user_handle, user_name, date_time, tweet]):
            logging.debug(instruction_index, entry_index, item_index)
    except:
        logging.error(instruction_index, entry_index, item_index)
        raise
    datetime_readable = process_datetime(date_time, human_readable=True)
    return (
        f'### <a href="{user_pfp}" target="_blank">'
        + f'<img src="{user_pfp}" {pfp_style} /></a>'
        + f" {user_name} *\(@{user_handle}\)*\n> — {datetime_readable}\n\n>{tweet}\n\n",
        item_index,
    )


def gen_page(json_object: dict, instruction_index: int, entry_index: int, convo: bool = False) -> None:
    """
    Generate page file after getting component bodies

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.
        entry_index (int): Index for the current entry.
        convo (bool): switch for multi vs single tweet entries

    Returns:
        Nothing

    Raises:
        TypeError: If an error occurs in parsing the entry.
    """
    tags = set()
    authors = set()
    main_bodies = []
    media_bodies = {}
    items = get_items(
        json_object, instruction_index, entry_index
    )  # a list of indexes, or [None]
    if convo:
        tags.add("conversation")
        item_index = 0
    else:
        tags.add(f"single {tweets_or_xeets}")
        item_index = None
    first_date_time = get_datetime(
        json_object, instruction_index, entry_index, item_index=items[0]
    )
    sanitized_datetime = process_datetime(first_date_time)
    filename = sanitized_datetime + ".md"
    os.makedirs(sys.argv[2], exist_ok=True)
    filepath = os.path.join(sys.argv[2], filename)

    # generate bodies and tags
    for item_index in items:
        main_bodies.append(
            gen_main_body(
                json_object, instruction_index, entry_index, authors, item_index
            )
        )
        media_bodies[item_index] = gen_media_body(
            json_object, instruction_index, entry_index, tags, item_index
        )

    # printout to file
    with open(filepath, "w", encoding="utf-8") as outfile:
        outfile.write(
            f"Title: {process_datetime(first_date_time, human_readable=True)}\n"
            f"Date: {first_date_time}\n"
            f"Category: Tweet\n"
            f"Tags: {','.join(tag for tag in tags if tag is not None)}\n"
            f"Authors: {','.join(author for author in authors if author is not None)}\n\n"
        )
        for body, item_index in main_bodies:
            outfile.write(body)
            if item_index in media_bodies:
                for media_item in media_bodies[item_index]:
                    outfile.write(media_item)


def parse_entry(
    json_object: dict, instruction_index: int, entry_index: int, entry_type: str
) -> None:
    """
    Parse a specific entry in the JSON object based on its type.

    Args:
        json_object (dict): The line being worked with.
        instruction_index (int): Index for the current instruction.
        entry_index (int): Index for the current entry.

    Raises:
        TypeError: If an error occurs in parsing the entry.
    """
    try:
        # other types aren't of interest to us (like cursors)
        if entry_type == "TimelineTimelineItem":
            gen_page(json_object, instruction_index, entry_index)
        elif entry_type == "TimelineTimelineModule":
            gen_page(json_object, instruction_index, entry_index, convo=True)
    except TypeError as e:
        logging.error(e, instruction_index, entry_index)
        raise


def parse_line(line_info: Tuple[int, str]) -> None:
    """
    Parses a line into JSON data and processes it.

    Args:
        line_info (Tuple[int, str]): A tuple containing the line number and the line data as a string.

    Raises:
        json.JSONDecodeError: If the line content is not valid JSON.
        OSError: If there is an error creating a file during processing.
        TypeError: If a TypeError occurs during processing.
        Exception: For any other unknown errors that occur.
    """
    line_number, line = line_info

    try:
        json_object = json.loads(line)
        # we now have a json object with all the data we wanna play with

        # let's make some markdown files
        for instruction_index in get_valid_instructions(json_object):
            for entry_index, entry_type in get_valid_entries(
                json_object, instruction_index
            ):
                parse_entry(json_object, instruction_index, entry_index, entry_type)
    except json.JSONDecodeError:
        logging.warning(f"Invalid JSON on line {line_number}")
    except OSError as e:
        logging.critical(f"Error creating file for line {line_number}: {e}")
    except TypeError as e:
        logging.warning(f"TypeError occured on line {line_number}: {e}")
    except Exception as e:
        logging.error(f"uknown error occured on line {line_number}: {e}")


def main():
    # open the archive
    with open(sys.argv[1], "r", encoding="utf-16") as infile:
        with multiprocessing.Pool() as pool:
            pool.map(parse_line, list(enumerate(infile, start=1)))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "-h":
        print("Valid invocation:\n\tpython parse.py infile.json output_directory")
        exit(0)
    start = time.perf_counter()
    main()
    end = time.perf_counter()
    total_time = end - start
    logging.debug(f"Total processing time: {total_time:.6f} seconds")
