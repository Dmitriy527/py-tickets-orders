from django.db.models import Prefetch, Q, Count, F
from rest_framework import viewsets

from cinema.models import (
    Genre,
    Actor,
    CinemaHall,
    Movie,
    MovieSession,
    Order,
    Ticket
)

from cinema.serializers import (
    GenreSerializer,
    ActorSerializer,
    CinemaHallSerializer,
    MovieSerializer,
    MovieSessionSerializer,
    MovieSessionListSerializer,
    MovieDetailSerializer,
    MovieSessionDetailSerializer,
    MovieListSerializer,
    OrderListSerializer,
    OrderCreateSerializer,
    TicketSerializer,
)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class CinemaHallViewSet(viewsets.ModelViewSet):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer

    def _params_to_string(self, query_string):
        return [string for string in query_string.split(",")]

    def get_queryset(self):
        queryset = self.queryset.prefetch_related("genres", "actors")
        title = self.request.query_params.get("title", None)
        actors = self.request.query_params.get("actors", None)
        genres = self.request.query_params.get("genres", None)
        filters = Q()
        if title:
            filters |= Q(title__icontains=title)
        if actors:
            actors = self._params_to_string(actors)

            for full_name in actors:
                try:
                    first, last = full_name.split(" ")
                    filters |= Q(
                        actors__first_name__iexact=first,
                        actors__last_name__iexact=last
                    )
                except ValueError:
                    continue
        if genres:
            genres = self._params_to_string(genres)
            filters |= Q(genres__name__in=genres)
        queryset = queryset.filter(filters)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer

        if self.action == "retrieve":
            return MovieDetailSerializer

        return MovieSerializer


class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = MovieSession.objects.prefetch_related(
        Prefetch(
            "tickets",
            queryset=Ticket.objects.all()
        )
    ).select_related(
        "movie",
        "cinema_hall"
    ).all()

    def get_queryset(self):
        if self.action == "list":
            queryset = (
                MovieSession.objects.prefetch_related(
                    Prefetch(
                        "tickets",
                        queryset=Ticket.objects.all()
                    )
                ).select_related("movie", "cinema_hall").annotate(
                    tickets_available=F(
                        "cinema_hall__rows"
                    ) * F(
                        "cinema_hall__seats_in_row"
                    ) - Count("tickets"))).all()
            date = self.request.query_params.get("date", None)
            movie = self.request.query_params.get("movie", None)
            filters = Q()
            if date and movie:
                filters |= Q(show_time__icontains=date)
                filters |= Q(id=movie)
            queryset = queryset.filter(filters)
        if self.action == "retrieve":
            queryset = self.queryset

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return MovieSessionListSerializer

        if self.action == "retrieve":
            return MovieSessionDetailSerializer

        return MovieSessionSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related(
        Prefetch(
            "tickets",
            queryset=Ticket.objects.select_related(
                "movie_session__movie",
                "movie_session__cinema_hall"
            )
        ),
    )
    serializer_class = OrderListSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderListSerializer
