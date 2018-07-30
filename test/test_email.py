from fermi_blind_search.process_blind_search_results import get_blocks

def test_two_blocks_first_block():
    event_dict = {"name": "two_blocks", "dec": 25.4, "ra": 12.3, "start_times": [11,17], "stop_times": [15,20],
                  "counts": [7,12], "probs": [0.1,0.2]}
    blocks = get_blocks(event_dict)

    assert len(blocks) == 1, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 11) and (blocks[0]["stop_time"] == 15), "returned the wrong block"

def test_two_blocks_second_block():
    event_dict = {"name": "two_blocks", "dec": 25.4, "ra": 12.3, "start_times": [11, 17], "stop_times": [15, 20],
                  "counts": [7, 12], "probs": [0.2, 0.1]}
    blocks = get_blocks(event_dict)

    assert len(blocks) == 1, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 17) and (blocks[0]["stop_time"] == 20), "returned the wrong block"

def test_three_blocks_middle_block():
    event_dict = {"name": "three_blocks", "dec": 25.4, "ra": 12.3, "start_times": [1,3,5], "stop_times": [2,4,6],
                  "counts": [7,7,7], "probs": [0.3,0.1,0.7]}
    blocks = get_blocks(event_dict)

    assert len(blocks) == 1, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 3) and (blocks[0]["stop_time"] == 4), "returned the wrong block"

def test_three_blocks_same_prob():
    event_dict = {"name": "three_blocks", "dec": 25.4, "ra": 12.3, "start_times": [1,3,5], "stop_times": [2,4,6],
                  "counts": [7,7,7], "probs": [0.3,0.3,0.7]}
    blocks = get_blocks(event_dict)

    assert len(blocks) == 1, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 1) and (blocks[0]["stop_time"] == 2), "returned the wrong block"

def test_four_blocks_continuous():
    event_dict = {"name": "three_blocks", "dec": 25.4, "ra": 12.3, "start_times": [1,3,5,7], "stop_times": [2,4,6,8],
                  "counts": [7,7,7,7], "probs": [0.1,0.05,0.2,0.3]}
    blocks = get_blocks(event_dict)

    assert len(blocks) == 1, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 1) and (blocks[0]["stop_time"] == 4), "returned the wrong block"

def test_four_blocks_noncontinuous():
    event_dict = {"name": "three_blocks", "dec": 25.4, "ra": 12.3, "start_times": [1, 3, 5, 7],
                  "stop_times": [2, 4, 6, 8],
                  "counts": [7, 7, 7, 7], "probs": [0.1,0.2,0.4,0.1]}
    blocks = get_blocks(event_dict)
    blocks = sorted(blocks, key=(lambda x: x["start_time"]))

    assert len(blocks) == 2, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 1) and (blocks[0]["stop_time"] == 2), "returned the wrong block"
    assert (blocks[1]["start_time"] == 7) and (blocks[1]["stop_time"] == 8), "returned the wrong block"

def test_four_blocks_same_prob():
    event_dict = {"name": "three_blocks", "dec": 25.4, "ra": 12.3, "start_times": [1, 3, 5, 7],
                  "stop_times": [2, 4, 6, 8],
                  "counts": [7, 7, 7, 7], "probs": [0.1,0.2,0.1,0.1]}
    blocks = get_blocks(event_dict)
    blocks = sorted(blocks, key=(lambda x: x["start_time"]))

    assert len(blocks) == 2, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 1) and (blocks[0]["stop_time"] == 2), "returned the wrong block"
    assert (blocks[1]["start_time"] == 5) and (blocks[1]["stop_time"] == 6), "returned the wrong block"

def test_five_blocks_first_two_continuous():
    event_dict = {"name": "three_blocks", "dec": 25.4, "ra": 12.3, "start_times": [1, 3, 5, 7, 9],
                  "stop_times": [2, 4, 6, 8, 10],
                  "counts": [7, 7, 7, 7, 7], "probs": [0.5,0.2,0.1,0.7,0.05]}
    blocks = get_blocks(event_dict)
    blocks = sorted(blocks, key=(lambda x: x["start_time"]))

    assert len(blocks) == 2, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 3) and (blocks[0]["stop_time"] == 6), "returned the wrong block"
    assert (blocks[1]["start_time"] == 9) and (blocks[1]["stop_time"] == 10), "returned the wrong block"

def test_five_blocks_noncontinuous():
    event_dict = {"name": "three_blocks", "dec": 25.4, "ra": 12.3, "start_times": [1, 3, 5, 7, 9],
                  "stop_times": [2, 4, 6, 8, 10],
                  "counts": [7, 7, 7, 7, 7], "probs": [0.1,0.2,0.1,0.7,0.05]}
    blocks = get_blocks(event_dict)
    blocks = sorted(blocks, key=(lambda x: x["start_time"]))

    assert len(blocks) == 3, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 1) and (blocks[0]["stop_time"] == 2), "returned the wrong block"
    assert (blocks[1]["start_time"] == 5) and (blocks[1]["stop_time"] == 6), "returned the wrong block"
    assert (blocks[2]["start_time"] == 9) and (blocks[2]["stop_time"] == 10), "returned the wrong block"

def test_five_blocks_second_two_continuous():
    event_dict = {"name": "three_blocks", "dec": 25.4, "ra": 12.3, "start_times": [1, 3, 5, 7, 9],
                  "stop_times": [2, 4, 6, 8, 10],
                  "counts": [7, 7, 7, 7, 7], "probs": [0.1,0.5,0.5,0.1,0.05]}
    blocks = get_blocks(event_dict)
    blocks = sorted(blocks, key=(lambda x: x["start_time"]))

    assert len(blocks) == 2, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 1) and (blocks[0]["stop_time"] == 2), "returned the wrong block"
    assert (blocks[1]["start_time"] == 7) and (blocks[1]["stop_time"] == 10), "returned the wrong block"

def test_five_blocks_three_continuous():
    event_dict = {"name": "three_blocks", "dec": 25.4, "ra": 12.3, "start_times": [1, 3, 5, 7, 9],
                  "stop_times": [2, 4, 6, 8, 10],
                  "counts": [7, 7, 7, 7, 7], "probs": [0.1,0.05,0.05,0.5,0.5]}
    blocks = get_blocks(event_dict)

    assert len(blocks) == 1, "returned wrong number of blocks"
    assert (blocks[0]["start_time"] == 1) and (blocks[0]["stop_time"] == 6), "returned the wrong block"
