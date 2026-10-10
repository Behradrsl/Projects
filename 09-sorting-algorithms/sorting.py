"""Three sorting algorithms. Each returns a sorted copy of the input."""


def bubble_sort(numbers: list[int]) -> list[int]:
    result = list(numbers)
    for end in range(len(result) - 1, 0, -1):
        swapped = False
        for index in range(end):
            if result[index] > result[index + 1]:
                result[index], result[index + 1] = result[index + 1], result[index]
                swapped = True
        if not swapped:
            break
    return result


def insertion_sort(numbers: list[int]) -> list[int]:
    result = list(numbers)
    for index in range(1, len(result)):
        value = result[index]
        previous = index - 1
        while previous >= 0 and result[previous] > value:
            result[previous + 1] = result[previous]
            previous -= 1
        result[previous + 1] = value
    return result


def selection_sort(numbers: list[int]) -> list[int]:
    result = list(numbers)
    for index in range(len(result) - 1):
        smallest = index
        for other in range(index + 1, len(result)):
            if result[other] < result[smallest]:
                smallest = other
        result[index], result[smallest] = result[smallest], result[index]
    return result


ALGORITHMS = {
    "bubble": bubble_sort,
    "insertion": insertion_sort,
    "selection": selection_sort,
}
