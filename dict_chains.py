"""
Dynamically generate required key arrays for plumbing JSON object

some functions hold an 'alt' argument, because there are items that occasionally crop up 
(about 6 in 12000 for me) that have 'tweet' inserted between 'restult' and 'legacy' keys
"""

instruction_chain = [
    "data",
    "user",
    "result",
    "timeline_v2",
    "timeline",
    "instructions",
]


def instruction_type_chain(instruction_index):
    return [instruction_index, "type"]


valid_instruction_type = "TimelineAddEntries"


def entry_chain(instruction_index):
    return instruction_chain + [
        instruction_index,
        "entries",
    ]


entry_type_name_chain = ["content", "__typename"]

valid_entry_types = ["TimelineTimelineModule", "TimelineTimelineItem"]

# This is for filtering follow recommends, which wind up in the data but aren't what we want.
# cursors still get through, but they're filtered by parseline()'s logic
invalid_entryid_type = "who-to-follow"


def entryid_chain(entry_index):
    return [entry_index, "entryId"]


def item_chain(instruction_index, entry_index):
    return entry_chain(instruction_index) + [
        entry_index,
        "content",
        "items",
    ]


def pre_chain(instruction_index, entry_index, item_index=None):
    if item_index is None:
        return entry_chain(instruction_index) + [
            entry_index,
            "content",
        ]
    else:
        return item_chain(instruction_index, entry_index) + [
            item_index,
            "item",
        ]


chain_mid = [
    "itemContent",
    "tweet_results",
    "result",
]


def datetime_chain(instruction_index, entry_index, item_index=None, alt=False):
    chain_pre = pre_chain(instruction_index, entry_index, item_index)

    chain_post = [
        "legacy",
        "created_at",
    ]
    if alt:
        chain_post.insert(0, "tweet")
    return chain_pre + chain_mid + chain_post


# defaults to user handle
def user_chain(instruction_index, entry_index, item_index=None, alt=False):
    chain_pre = pre_chain(instruction_index, entry_index, item_index)

    chain_post = [
        "core",
        "user_results",
        "result",
        "legacy",
    ]
    if alt:
        chain_post.insert(0, "tweet")
    user_info_chain = chain_pre + chain_mid + chain_post
    return (
        user_info_chain + ["profile_image_url_https"],
        user_info_chain + ["screen_name"],
        user_info_chain + ["name"],
    )


def media_chain(instruction_index, entry_index, item_index=None, alt=False):
    chain_pre = pre_chain(instruction_index, entry_index, item_index)

    chain_post = [
        "legacy",
        "entities",
        "media",
    ]

    if alt:
        chain_post.insert(0, "tweet")
    return chain_pre + chain_mid + chain_post


def media_url_chain(variation_index=None):
    if variation_index is None:
        return ["media_url_https"]
    else:
        return [
            "video_info",
            "variants",
            variation_index,
            "url",
        ]


media_url_direct_chain = ["expanded_url"]
media_type_chain = ["type"]
media_variants_chain = ["video_info", "variants"]


def tweet_chain(instruction_index, entry_index, item_index=None, alt=False):
    chain_pre = pre_chain(instruction_index, entry_index, item_index)
    chain_post = [
        "legacy",
        "full_text",
    ]
    if alt:
        chain_post.insert(0, "tweet")
    return chain_pre + chain_mid + chain_post
